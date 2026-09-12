/* Convert official SVG assets to proportional PNGs for reliable nested-image rendering. */
const fs=require('fs');
const path=require('path');
const sharp=require(process.env.SPENDLY_SHARP_PATH || 'C:/Users/evagh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const assets=path.resolve(__dirname,'../assets');
(async()=>{
  for(const filename of fs.readdirSync(assets).filter(f=>f.endsWith('.svg'))){
    // Trim only transparent renderer padding; preserve the complete logo artwork.
    await sharp(path.join(assets,filename),{density:300}).trim().resize({width:800,height:800,fit:'inside'}).png().toFile(path.join(assets,filename.replace('.svg','_render.png')));
  }
})().catch(e=>{console.error(e);process.exit(1)});
