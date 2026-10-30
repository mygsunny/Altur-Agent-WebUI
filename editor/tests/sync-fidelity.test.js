import test from 'node:test';
import assert from 'node:assert/strict';
import {DOMParser} from '@xmldom/xmldom';
import ExcelJS from 'exceljs';
import JSZip from 'jszip';
import {decodeOffice,encodeOffice} from '../src/office-sync.js';
globalThis.DOMParser=class extends DOMParser{parseFromString(...args){const doc=super.parseFromString(...args);doc.querySelectorAll=()=>Array.from(doc.getElementsByTagName('*'));return doc;}};
for(const feature of ['hidden','definedName','rowHeight','columnWidth','unknownPart'])test('reject XLSX '+feature,async()=>{
 const wb=new ExcelJS.Workbook(),ws=wb.addWorksheet('Sheet1');ws.getCell('A1').value='retained';
 if(feature==='hidden')ws.state='hidden';
 if(feature==='definedName')wb.definedNames.add('Sheet1!$A$1','secret');
 if(feature==='rowHeight')ws.getRow(1).height=35;
 if(feature==='columnWidth')ws.getColumn(1).width=55;
 let bytes=await wb.xlsx.writeBuffer();
 if(feature==='unknownPart'){const z=await JSZip.loadAsync(bytes);z.file('xl/customFeature.xml','<feature/>');bytes=await z.generateAsync({type:'uint8array'});}
 await assert.rejects(decodeOffice(bytes,'sheet'),/Unsupported/);
});
for(const feature of ['hidden','rowData','columnData','unknown'])test('reject native '+feature,async()=>{
 const sheet={id:'s',name:'Sheet1',rowCount:1000,columnCount:100,cellData:{}};
 sheet[feature]=feature==='hidden'?1:{0:{h:99}};
 await assert.rejects(encodeOffice({id:'book',name:'Book',sheetOrder:['s'],sheets:{s:sheet}},'sheet'),/Unsupported/);
});

test('plain generated XLSX and DOCX pass whole-package gate',async()=>{
 const wb=new ExcelJS.Workbook();wb.addWorksheet('Sheet1').getCell('A1').value='plain';
 assert.equal((await decodeOffice(await wb.xlsx.writeBuffer(),'sheet')).sheets.sheet1.cellData[0][0].v,'plain');
 const {Document,Packer,Paragraph}=await import('docx');
 assert.equal((await decodeOffice(await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('plain')]}]})),'document')).content[0].content[0].text,'plain');
});
for(const feature of ['paragraphAttribute','metadata','relationship','unknownPart'])test('reject DOCX '+feature,async()=>{
 const {Document,Packer,Paragraph}=await import('docx');
 const z=await JSZip.loadAsync(await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('plain')]}]})));
 if(feature==='unknownPart')z.file('word/unknown.xml','<feature/>');
 else{
  const name=feature==='paragraphAttribute'?'word/document.xml':feature==='metadata'?'docProps/core.xml':'word/_rels/document.xml.rels';
  const xml=await z.file(name).async('string');
  z.file(name,feature==='paragraphAttribute'?xml.replace('<w:p>','<w:p w:rsidR="FFFF">'):feature==='metadata'?xml.replace('</cp:coreProperties>','<cp:keywords>retained metadata</cp:keywords></cp:coreProperties>'):xml.replace('</Relationships>','<Relationship Id="extra" Type="unknown" Target="secret"/></Relationships>'));
 }
 await assert.rejects(decodeOffice(await z.generateAsync({type:'uint8array'}),'document'),/Unsupported/);
});
