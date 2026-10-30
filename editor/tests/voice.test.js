import test from 'node:test';
import assert from 'node:assert/strict';
import {PhraseGate} from '../src/voice.js';
test('silence finalizes sequential phrases without stopping listening',()=>{
 const gate=new PhraseGate();const finals=[];
 for(const [level,time] of [[.1,0],[.1,300],[0,500],[0,1400],[.1,2000],[.1,2300],[0,2500],[0,3400]])if(gate.sample(level,time))finals.push(time);
 assert.deepEqual(finals,[1400,3400]);
});
test('silence and brief clicks do not submit audio',()=>{const gate=new PhraseGate();assert.equal(gate.sample(0,0),false);assert.equal(gate.sample(.1,100),false);assert.equal(gate.sample(0,1000),false);});
test('long speech is bounded and reset discards pending phrase',()=>{const gate=new PhraseGate();gate.sample(.1,0);assert.equal(gate.sample(.1,20000),true);gate.sample(.1,21000);gate.reset();assert.equal(gate.sample(0,23000),false);});
