import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
const lock=JSON.parse(fs.readFileSync('package-lock.json','utf8'));
const allowed=new Set(['MIT','MIT/X11','Apache-2.0','ISC','BSD','BSD-2-Clause','BSD-3-Clause','0BSD','Unlicense','(MIT AND Zlib)','(MIT OR GPL-3.0-or-later)']);
const inventory=[],notices=[];
for(const [location,entry] of Object.entries(lock.packages)){
 if(!location||entry.dev)continue;
 const folder=path.resolve(location);if(!fs.existsSync(path.join(folder,'package.json')))continue; // other-platform optional binaries
 const meta=JSON.parse(fs.readFileSync(path.join(folder,'package.json'),'utf8'));
 const license=meta.license||entry.license||(meta.licenses||[]).map(l=>l.type).join(' OR ');
 if(!allowed.has(license))throw Error('Unverified OSS license: '+meta.name+' '+license);
 inventory.push({name:meta.name,version:meta.version,license});
 let text='';
 for(const name of fs.readdirSync(folder))if(/^(licen[sc]e|copying|notice)(\.|$)/i.test(name)&&fs.statSync(path.join(folder,name)).isFile())text+='\n'+fs.readFileSync(path.join(folder,name),'utf8');
 notices.push('## '+meta.name+'@'+meta.version+' — '+license+'\n'+(text||'License metadata: '+license+'; see published package repository for full terms.'));
}
inventory.sort((a,b)=>a.name.localeCompare(b.name));
fs.writeFileSync('../static/cowork/licenses.json',JSON.stringify(inventory,null,2)+'\n');
fs.writeFileSync('../static/cowork/THIRD-PARTY-NOTICES.txt','Co-work OSS dependencies. Dual-licensed MIT/GPL code is used under MIT.\n\n'+notices.join('\n\n').replace(/\r\n/g,'\n').replace(/[ \t]+$/gm,''));
console.log('Verified OSS metadata for '+inventory.length+' installed production packages; notices generated.');
const out='../static/cowork';
const manifest=fs.readdirSync(out,{recursive:true}).filter(name=>name!=='manifest.json'&&fs.statSync(path.join(out,name)).isFile()).sort().map(name=>{
 const bytes=fs.readFileSync(path.join(out,name));return {path:'static/cowork/'+name,bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};
});
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
