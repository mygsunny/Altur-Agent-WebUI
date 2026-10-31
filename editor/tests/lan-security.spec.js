import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
const base=process.env.COWORK_LAN_URL;
test.skip(!base,'Set COWORK_LAN_URL to an actual insecure LAN trial origin');
test('LAN server retains login, CSRF, atomic competing claims and foreign-owner write refusal',async({request})=>{
 expect((await request.get(base+'/api/cowork/document?id=anonymous-fixture')).status()).toBe(401);
 expect((await request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(process.env.COWORK_PASSWORD_FILE,'utf8')},headers:{Origin:base}})).status()).toBe(200);
 const html=await (await request.get(base)).text(),csrf=JSON.parse(html.match(/csrfToken:("(?:[^"\\]|\\.)*")/)[1]);
 const document_id=randomUUID(),owners=[randomUUID(),randomUUID()],headers={Origin:base,'X-Hermes-CSRF-Token':csrf};
 const claims=await Promise.all(owners.map(owner=>request.post(base+'/api/cowork/claim',{headers,data:{profile:'default',document_id,owner}})));
 expect(claims.map(r=>r.status()).sort()).toEqual([200,409]);
 const winner=claims.findIndex(r=>r.status()===200),payload={profile:'default',document_id,owner:owners[winner],revision:0,kind:'document',snapshot:{type:'doc',content:[{type:'paragraph'}]}};
 expect((await request.post(base+'/api/cowork/document',{headers:{Origin:base,'X-Hermes-CSRF-Token':'invalid'},data:payload})).status()).toBe(403);
 expect((await request.post(base+'/api/cowork/document',{headers,data:{...payload,owner:owners[1-winner]}})).status()).toBe(409);
 expect((await request.post(base+'/api/cowork/document',{headers,data:payload})).status()).toBe(200);
 expect((await request.post(base+'/api/cowork/document',{headers,data:payload})).status()).toBe(409);
 const stored=await (await request.get(base+'/api/cowork/document?id='+document_id)).json();expect(stored.document.revision).toBe(1);
});
