import ExcelJS from 'exceljs';
import {Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell} from 'docx';

// Deliberately bounded exchange, NOT Office fidelity. UI requires explicit
// acknowledgment before import. Native snapshots are the full working format.
export async function sheetToXlsx(snapshot){
 const wb=new ExcelJS.Workbook();
 for(const id of snapshot.sheetOrder){
  const s=snapshot.sheets[id],ws=wb.addWorksheet(s.name);
  for(const [r,row] of Object.entries(s.cellData||{}))for(const [c,cell] of Object.entries(row)){
   if(cell.p)throw Error('Unsupported rich cell; use native snapshot export');
   ws.getCell(+r+1,+c+1).value=cell.f?{formula:cell.f.replace(/^=/,'')}:cell.v??null;
  }
 }
 return wb.xlsx.writeBuffer();
}
export async function xlsxToSheet(buffer){
 const wb=new ExcelJS.Workbook();await wb.xlsx.load(buffer);
 if(!wb.worksheets.length)throw Error('No worksheets');
 const sheets={},sheetOrder=[];
 for(const ws of wb.worksheets){
  if(ws.rowCount>1000||ws.columnCount>100)throw Error('Import limit: 1000 rows × 100 columns');
  const id='sheet'+ws.id,cellData={};sheetOrder.push(id);
  ws.eachRow((row,r)=>row.eachCell((cell,c)=>{
   const v=cell.value;if(v===null)return;
   let data;if(typeof v==='object'){
    if(typeof v.formula!=='string')throw Error('Unsupported date, rich text, error, hyperlink or shared formula cell');
    data={f:'='+v.formula};
   }else if(['string','number','boolean'].includes(typeof v))data={v};
   else throw Error('Unsupported cell');
   (cellData[r-1]??={})[c-1]=data;
  }));
  sheets[id]={id,name:ws.name,rowCount:1000,columnCount:100,cellData};
 }
 return {id:'import-'+Date.now(),name:'Imported spreadsheet',sheets,sheetOrder};
}
function runs(node){
 return (node.content||[]).map(n=>{
  if(n.type==='hardBreak')return new TextRun({break:1});
  if(n.type!=='text')throw Error('Unsupported inline node: '+n.type);
  const marks=new Set((n.marks||[]).map(m=>m.type));
  if([...marks].some(m=>!['bold','italic','strike','underline'].includes(m)))throw Error('Unsupported text formatting; export native snapshot');
  return new TextRun({text:n.text,bold:marks.has('bold')?true:undefined,italics:marks.has('italic')?true:undefined,strike:marks.has('strike')?true:undefined,underline:marks.has('underline')?{}:undefined});
 });
}
function block(n){
 if(n.type==='paragraph'||n.type==='heading')return new Paragraph({children:runs(n),heading:n.type==='heading'?'Heading'+n.attrs.level:undefined});
 if(n.type==='table')return new Table({rows:n.content.map(row=>new TableRow({children:row.content.map(cell=>{
  if((cell.attrs?.colspan||1)!==1||(cell.attrs?.rowspan||1)!==1)throw Error('Unsupported merged DOCX table cells');
  return new TableCell({children:cell.content.map(block)});
 })}))});
 throw Error('Unsupported DOCX export node: '+n.type+'; export native snapshot instead');
}
export async function documentToDocx(snapshot){return Packer.toArrayBuffer(new Document({sections:[{children:(snapshot.content||[]).map(block)}]}));}
export async function docxToHtml(buffer){
 const {default:mammoth}=await import('mammoth/mammoth.browser');
 const result=await mammoth.convertToHtml({arrayBuffer:buffer});
 if(result.messages.length)throw Error('DOCX has unsupported features: '+result.messages.map(m=>m.message).join('; '));
 const doc=new DOMParser().parseFromString(result.value,'text/html');
 const allowed=new Set(['P','STRONG','EM','U','S','H1','H2','H3','H4','H5','H6','TABLE','TBODY','TR','TD','TH','BR']);
 for(const node of doc.body.querySelectorAll('*')){
  if(!allowed.has(node.tagName))throw Error('Unsupported DOCX content: '+node.tagName);
  for(const attr of [...node.attributes])if(!['colspan','rowspan'].includes(attr.name))node.removeAttribute(attr.name);
 }
 return doc.body.innerHTML;
}
