import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash,webcrypto} from 'node:crypto';
import {randomId,snapshotHash} from '../src/browser-capabilities.js';
test('HTTP UUID and SHA-256 fallback match secure primitives without changing globals',async()=>{
 const original=Object.getOwnPropertyDescriptor(globalThis,'crypto');
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)}});
 try{
  const ids=new Set(Array.from({length:100},()=>randomId()));assert.equal(ids.size,100);
  for(const id of ids)assert.match(id,/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
  for(const snapshot of [{}, {text:'中文 🎉',rows:[1,2,3]}, {text:'a'.repeat(10000)}])assert.equal(await snapshotHash(snapshot),createHash('sha256').update(JSON.stringify(snapshot)).digest('hex'));
  assert.equal(crypto.randomUUID,undefined);assert.equal(crypto.subtle,undefined);
 }finally{Object.defineProperty(globalThis,'crypto',original);}
});
