// Load the isolated editor bundle only when requested; chat/workers stay mounted.
(() => {
 const trigger=document.getElementById('btnCowork');if(!trigger)return;
 let dialog,frame;
 trigger.addEventListener('click',()=>{
  if(!dialog){
   dialog=document.createElement('dialog');dialog.setAttribute('aria-label','Co-work editor');
   dialog.style.cssText='width:96vw;height:94vh;max-width:none;max-height:none;padding:0;border:1px solid var(--border);background:var(--bg);';
   const close=document.createElement('button');close.textContent='Close Co-work';close.style.cssText='position:absolute;right:12px;top:4px;z-index:10;';
   close.onclick=()=>dialog.close();dialog.append(close);
   frame=document.createElement('iframe');frame.title='Spreadsheet and document co-work';frame.src='/static/cowork/index.html';frame.allow='microphone';frame.style.cssText='width:100%;height:100%;border:0;padding-top:30px;';dialog.append(frame);document.body.append(dialog);
   // Closing hides, not destroys: ownership/model/unsaved edits remain intact.
   dialog.addEventListener('close',()=>{frame.contentWindow?.cowork?.controller.stop();frame.contentWindow?.cowork?.pauseVoice?.();trigger.focus();});
  }
  dialog.showModal();
 });
})();
