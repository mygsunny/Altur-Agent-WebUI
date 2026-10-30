import {randomId} from './browser-capabilities.js';
import {createUniver,LocaleType,mergeLocales} from '@univerjs/presets';
import {UniverSheetsCorePreset} from '@univerjs/preset-sheets-core';
import enUS from '@univerjs/preset-sheets-core/locales/en-US';
import '@univerjs/preset-sheets-core/lib/index.css';

export function bounds(notation){
 if(typeof notation!=='string'||!/^([A-Z]{1,3})([1-9][0-9]*)(?::([A-Z]{1,3})([1-9][0-9]*))?$/.test(notation))throw Error('Use an explicit A1 cell/range');
 const m=notation.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/), col=s=>[...s].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)-1;
 const r=+m[2]-1,c=col(m[1]),er=+(m[4]||m[2])-1,ec=col(m[3]||m[1]);
 if(r>er||c>ec||er>=1000||ec>=100)throw Error('Supported targeted range is A1:CV1000');
 return {r,c,rows:er-r+1,cols:ec-c+1};
}
export class SheetAdapter {
 constructor(element,snapshot){
  const {univer,univerAPI}=createUniver({locale:LocaleType.EN_US,locales:{[LocaleType.EN_US]:mergeLocales(enUS)},presets:[UniverSheetsCorePreset({container:element})]});
  this.univer=univer;this.api=univerAPI;this.book=univerAPI.createWorkbook(snapshot||{id:randomId(),name:'Spreadsheet',sheetOrder:['sheet1'],sheets:{sheet1:{id:'sheet1',name:'Sheet1',rowCount:1000,columnCount:100,cellData:{}}}});
 }
 snapshot(){return this.book.save();}
 context(){const sheet=this.book.getActiveSheet();return {kind:'sheet',sheet_id:sheet.getSheetId(),sheets:this.book.getSheets().map(s=>({id:s.getSheetId(),name:s.getSheetName()})),selection:sheet.getActiveRange()?.getA1Notation()||'A1',values:sheet.getRange('A1:T50').getValues(),formulas:sheet.getRange('A1:T50').getFormulas(),context_limit:'Only A1:T50 included; ask for clarification for unknown semantic targets'};}
 undo(){this.book.undo();}
 redo(){this.book.redo();}
 apply(op){
  if(op.type==='undo')return this.undo();if(op.type==='redo')return this.redo();
  if(op.type!=='sheet.set')throw Error('Unsupported spreadsheet operation');
  const sheet=this.book.getSheetBySheetId(op.sheet_id);if(!sheet)throw Error('Sheet target deleted; please clarify');
  const {rows,cols}=bounds(op.range);
  if(!Array.isArray(op.values)||op.values.length!==rows||op.values.some(row=>!Array.isArray(row)||row.length!==cols||row.some(v=>v!==null&&!['string','number','boolean'].includes(typeof v))))throw Error('Cell matrix does not match target');
  // Facade setValues executes one native set-range-values command/history item.
  sheet.getRange(op.range).setValues(op.values);
 }
 destroy(){this.univer.dispose();}
}
