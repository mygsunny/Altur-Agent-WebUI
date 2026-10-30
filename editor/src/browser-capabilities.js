import {sha256} from '@noble/hashes/sha256';
// getRandomValues remains available on HTTP; never use Math.random for owners.
export function randomId(){
 if(crypto.randomUUID)return crypto.randomUUID();
 const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
 return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
export async function snapshotHash(snapshot){
 const bytes=new TextEncoder().encode(JSON.stringify(snapshot));
 const digest=crypto.subtle?new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)):sha256(bytes);
 return Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('');
}
