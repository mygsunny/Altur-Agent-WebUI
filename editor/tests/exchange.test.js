import {test} from 'node:test';import assert from 'node:assert/strict';
test('genuine XLSX preserves number/string/formula and rejects unsupported cells',async()=>{
 const {sheetToXlsx,xlsxToSheet}=await import('../src/exchange.js');
 const data={id:'book',name:'Test',sheetOrder:['s'],sheets:{s:{id:'s',name:'Test',rowCount:1000,columnCount:100,cellData:{0:{0:{v:2},1:{v:'中文'},2:{f:'=A1*2'}}}}}};
 const buffer=await sheetToXlsx(data); assert.equal(new Uint8Array(buffer)[0],80);
 const result=await xlsxToSheet(buffer);const cells=Object.values(result.sheets)[0].cellData;
 assert.equal(cells[0][0].v,2);assert.equal(cells[0][1].v,'中文');assert.equal(cells[0][2].f,'=A1*2');
 const {default:ExcelJS}=await import('exceljs');const unsupported=new ExcelJS.Workbook();unsupported.addWorksheet('Date').getCell('A1').value=new Date('2026-01-01');
 const dateBytes=await unsupported.xlsx.writeBuffer();await assert.rejects(()=>xlsxToSheet(dateBytes),/Unsupported/);
});
test('genuine DOCX contains paragraph/table text and refuses unexportable nodes',async()=>{
 const {documentToDocx}=await import('../src/exchange.js'); const mammoth=await import('mammoth');
 const p=t=>({type:'paragraph',content:[{type:'text',text:t}]});
 const buffer=await documentToDocx({type:'doc',content:[p('Hello 中文'),{type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Cell')]}]}]}]});
 const result=await mammoth.default.extractRawText({buffer:Buffer.from(buffer)});assert.match(result.value,/Hello 中文/);assert.match(result.value,/Cell/);
 await assert.rejects(()=>documentToDocx({type:'doc',content:[{type:'image'}]}),/Unsupported/);
});
