"""Float32 inference for the fixed V6 LSTM, plus numeric Isolation Forest trees.

This executes the trained LSTM equations, not a linear-regression approximation.
Supports only the explicitly exported architecture. No TensorFlow, h5py, pickle
or training required in the serving process.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from .features import FORECAST_FEATURES,ANOMALY_VIEWS,next_week_features,anomaly_features


def average_path(n):
    n=np.asarray(n,dtype=float)
    result=np.zeros_like(n)
    result[n==2]=1.
    mask=n>2
    result[mask]=2.*(np.log(n[mask]-1.)+np.euler_gamma)-2.*(n[mask]-1.)/n[mask]
    return result


class PortableSelectedModel:
    def __init__(self,directory,*,allow_unverified_export=False):
        directory=Path(directory)
        self.metadata=json.loads((directory/'manifest.json').read_text())
        if self.metadata.get('format')!='spendly-portable-v6-v1':raise ValueError('Unsupported portable model')
        path=directory/'weights.npz'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=self.metadata['weights_sha256']:raise ValueError('Model checksum mismatch')
        if not allow_unverified_export:
            parity_path=directory/'parity.json'
            if not parity_path.is_file():raise ValueError('Export parity verification required')
            parity=json.loads(parity_path.read_text())
            if parity.get('passed') is not True or parity.get('weights_sha256')!=self.metadata['weights_sha256']:
                raise ValueError('Export parity identity mismatch')
        with np.load(path,allow_pickle=False) as arrays:self.w={k:arrays[k] for k in arrays.files}
        shapes={'kernel':(2,128),'recurrent':(32,128),'bias':(128,),
            'dense_kernel':(42,16),'dense_bias':(16,),'output_kernel':(16,1),'output_bias':(1,),
            'sequence_mean':(2,),'sequence_scale':(2,),'context_mean':(10,),'context_scale':(10,)}
        for key,shape in shapes.items():
            if self.w[key].shape!=shape or not np.isfinite(self.w[key]).all():raise ValueError('Invalid '+key)
        if (self.w['sequence_scale']<=0).any() or (self.w['context_scale']<=0).any():raise ValueError('Invalid scales')
        self.threshold=float(self.metadata['threshold'])
        if not np.isfinite(self.threshold):raise ValueError('Invalid alert threshold')
        if self.metadata.get('trees')!=300 or self.metadata.get('max_samples')!=128:
            raise ValueError('Unsupported forest dimensions')
        for t in range(self.metadata['trees']):
            prefix=f'tree{t}_';keys=['left','right','feature','threshold','samples']
            arrays=[self.w[prefix+k] for k in keys];n=len(arrays[0])
            if not n or any(a.shape!=(n,) for a in arrays):raise ValueError('Invalid tree shape')
            left,right,feature,threshold,samples=arrays
            internal=left!=-1
            if not np.isfinite(threshold).all() or (samples<=0).any():raise ValueError('Invalid tree values')
            for child in (left,right):
                if not np.issubdtype(child.dtype,np.integer) or ((child<-1)|(child>=n)).any():raise ValueError('Invalid tree child')
                if (child[internal]<=np.arange(n)[internal]).any():raise ValueError('Tree contains backwards/cyclic edges')
            if not np.array_equal(left==-1,right==-1) or ((feature[internal]<0)|(feature[internal]>=5)).any():raise ValueError('Invalid tree split')

    def residual(self,sequence,context):
        s=np.asarray(sequence,dtype=np.float32);x=np.asarray(context,dtype=np.float32)
        if s.ndim!=3 or s.shape[1:]!=(8,2) or x.shape!=(len(s),10):raise ValueError('Input shape mismatch')
        if not np.isfinite(s).all() or not np.isfinite(x).all():raise ValueError('Nonfinite input')
        # Match sklearn's float32 in-place subtract/divide order.
        s=s.copy();s-=self.w['sequence_mean'];s/=self.w['sequence_scale']
        x=x.copy();x-=self.w['context_mean'];x/=self.w['context_scale']
        hidden=np.zeros((len(s),32),np.float32);cell=np.zeros_like(hidden)
        sigmoid=lambda a: 1./(1.+np.exp(-np.clip(a,-80,80)))
        for t in range(8):
            gates=s[:,t]@self.w['kernel']+hidden@self.w['recurrent']+self.w['bias']
            i,f,c,o=np.split(gates,4,axis=1)
            cell=sigmoid(f)*cell+sigmoid(i)*np.tanh(c)
            hidden=sigmoid(o)*np.tanh(cell)
        dense=np.maximum(0.,np.concatenate([hidden,x],axis=1)@self.w['dense_kernel']+self.w['dense_bias'])
        return (dense@self.w['output_kernel']+self.w['output_bias']).ravel()

    def predict_features(self,features,scale,recurring):
        if list(features.columns)!=list(FORECAST_FEATURES):raise ValueError('Feature order mismatch')
        values=features.to_numpy(float)
        sequence=np.stack([values[:,:8][:,::-1],values[:,8:16][:,::-1]],axis=-1)
        scale=np.asarray(scale,float);recurring=np.asarray(recurring,float)
        if scale.shape!=(len(values),) or recurring.shape!=scale.shape or not np.isfinite(scale).all() or not np.isfinite(recurring).all() or (scale<=0).any():raise ValueError('Invalid scale/offset')
        return np.maximum(0.,self.residual(sequence,values[:,16:])*scale+recurring)

    def anomaly_scores(self,features):
        if (features[ANOMALY_VIEWS['excess']].to_numpy(float)<0).any():raise ValueError('Negative anomaly inputs')
        x=np.log1p(features[ANOMALY_VIEWS['excess']].to_numpy(float)).astype(np.float32)
        if not np.isfinite(x).all():raise ValueError('Invalid anomaly features')
        depth=np.zeros(len(x))
        for t in range(self.metadata['trees']):
            prefix=f'tree{t}_';left=self.w[prefix+'left'];right=self.w[prefix+'right']
            feature=self.w[prefix+'feature'];threshold=self.w[prefix+'threshold'];samples=self.w[prefix+'samples']
            nodes=np.zeros(len(x),dtype=int);steps=np.zeros(len(x))
            while True:
                active=np.flatnonzero(left[nodes]!=-1)
                if not len(active):break
                selected=nodes[active]
                nodes[active]=np.where(x[active,feature[selected]]<=threshold[selected],left[selected],right[selected])
                steps[active]+=1
            depth+=steps+average_path(samples[nodes])
        denominator=self.metadata['trees']*average_path(np.array([self.metadata['max_samples']]))[0]
        return 2.**(-depth/denominator)
