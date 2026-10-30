import {Editor} from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {TableKit} from '@tiptap/extension-table';
import {closeHistory} from '@tiptap/pm/history';

const paragraph=text=>({type:'paragraph',content:text?[{type:'text',text}]:[]});
export class DocumentAdapter {
 constructor(element,snapshot){this.editor=new Editor({element,extensions:[StarterKit,TableKit],editorProps:{attributes:{'aria-label':'Document page','data-placeholder':'Start typing your document…'}},content:snapshot||{type:'doc',content:[paragraph('')]}});}
 snapshot(){return this.editor.getJSON();}
 context(){const {from,to}=this.editor.state.selection;return {kind:'document',text:this.editor.getText().slice(0,60000),selection:{from,to,text:this.editor.state.doc.textBetween(from,to,'\n')}};}
 undo(){this.editor.commands.undo();}
 redo(){this.editor.commands.redo();}
 apply(op){
  if(op.type==='undo')return this.undo(); if(op.type==='redo')return this.redo();
  const {state,view}=this.editor;
  let tr=state.tr;
  if(op.type==='document.replace'){
   if(typeof op.find!=='string'||!op.find||typeof op.text!=='string')throw Error('Invalid replacement');
   const matches=[];
   state.doc.descendants((node,pos)=>{
    if(!node.isTextblock)return;
    // Text-only inline paragraphs/headings: marks retain their PM positions.
    let plain=true;node.forEach(child=>{if(!child.isText)plain=false});if(!plain)return;
    let start=0;while((start=node.textContent.indexOf(op.find,start))!==-1){matches.push({from:pos+1+start,to:pos+1+start+op.find.length});start++;}
   });
   if(matches.length!==1)throw Error('Target missing or ambiguous in current document; please clarify');
   tr=tr.insertText(op.text,matches[0].from,matches[0].to);
  }else if(op.type==='document.append'){
   if(typeof op.text!=='string')throw Error('Invalid text');
   const nodes=op.text.split('\n').map(t=>state.schema.nodeFromJSON(paragraph(t)));
   tr=tr.insert(state.doc.content.size,nodes);
  }else if(op.type==='document.table'){
   if(!Array.isArray(op.rows)||!op.rows.length||op.rows.some(r=>!Array.isArray(r)||r.length!==op.rows[0].length||r.some(c=>typeof c!=='string')))throw Error('Invalid table');
   const table={type:'table',content:op.rows.map(row=>({type:'tableRow',content:row.map(text=>({type:'tableCell',content:[paragraph(text)]}))}))};
   tr=tr.insert(state.doc.content.size,state.schema.nodeFromJSON(table));
  }else throw Error('Unsupported document operation');
  view.dispatch(closeHistory(tr));
  view.dispatch(closeHistory(this.editor.state.tr));
 }
 destroy(){this.editor.destroy();}
}
