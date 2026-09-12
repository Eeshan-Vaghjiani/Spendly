/* Render the exact SVGs to PNG; no browser, app server, or PDF is required. */
const fs = require('fs');
const path = require('path');
const sharp = require(process.env.SPENDLY_SHARP_PATH || 'C:/Users/evagh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname,'manifest.json'),'utf8'));
fs.mkdirSync(path.join(root,'png'),{recursive:true});
(async()=>{
  for(const fig of manifest){
    const target = fig.name.includes('Wireframe_') && fig.width<1000 ? 1800 : 4000;
    const input=path.join(root,'svg',fig.name+'.svg');
    await sharp(input,{density:144}).resize({width:target}).flatten({background:'#ffffff'}).png().toFile(path.join(root,'png',fig.name+'.png'));
    console.log(fig.name);
  }
})().catch(e=>{console.error(e);process.exit(1)});
