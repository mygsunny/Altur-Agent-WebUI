/* Direct navigation-rail ordering. Shares tab_order and autosave with Settings. */
(function(){
  'use strict';
  const rail=document.querySelector('.rail');
  if(!rail) return;
  // Global compose action: leave the current page through its normal guard first.
  window.openRailNewChat=async function(){
    if(await switchPanel('chat')===false) return;
    const button=document.getElementById('btnNewChat');
    if(button&&typeof button.onclick==='function') await button.onclick();
  };
  let editing=false, gesture=null, timer=null, suppressUntil=0;
  const selector='#btnRailNewChat, .rail-btn.nav-tab[data-panel]:not([data-panel="settings"]):not([data-dashboard-link])';
  const orderKey=button=>button.id==='btnRailNewChat'?'__new_chat__':button.dataset.panel;
  const movable=node=>node&&node.closest&&node.closest(selector);
  function clearTimer(){if(timer!==null){clearTimeout(timer);timer=null;}}
  function release(){
    clearTimer();
    if(gesture){
      const {button,id}=gesture;
      gesture=null;
      button.classList.remove('rail-dragging');
      if(button.hasPointerCapture(id)) button.releasePointerCapture(id);
    }
    rail.querySelectorAll('.rail-drop-target').forEach(node=>node.classList.remove('rail-drop-target'));
  }
  function edit(){editing=true;rail.classList.add('rail-editing');rail.setAttribute('aria-label','Reorder navigation. Drag icons, or use Alt and arrow keys. Escape to finish.');}
  function finish(){if(gesture&&gesture.active||suppressUntil===Infinity)suppressUntil=Date.now()+400;release();editing=false;rail.classList.remove('rail-editing');rail.setAttribute('aria-label','Primary navigation');}
  function startDrag(){
    if(!gesture||!gesture.button.isConnected) return release();
    edit();gesture.active=true;suppressUntil=Infinity;
    gesture.button.classList.add('rail-dragging');
    try{gesture.button.setPointerCapture(gesture.id);}catch(_){/* Synthetic tests and released pointers. */}
  }
  rail.addEventListener('pointerdown',event=>{
    if(event.button!==0||event.isPrimary===false) return;
    const button=movable(event.target);
    if(!button||button.closest('.rail')!==rail||button.classList.contains('nav-tab-hidden')) return;
    release();
    gesture={button,id:event.pointerId,x:event.clientX,y:event.clientY,active:false,target:null};
    if(editing){event.preventDefault();startDrag();}
    else timer=setTimeout(startDrag,500);
  });
  rail.addEventListener('pointermove',event=>{
    if(!gesture||event.pointerId!==gesture.id) return;
    if(!gesture.active){
      if(Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)>8) release();
      return;
    }
    event.preventDefault();
    const target=movable(document.elementFromPoint(event.clientX,event.clientY));
    rail.querySelectorAll('.rail-drop-target').forEach(node=>node.classList.remove('rail-drop-target'));
    gesture.target=target&&target.closest('.rail')===rail&&!target.classList.contains('nav-tab-hidden')?target:null;
    if(gesture.target&&gesture.target!==gesture.button) gesture.target.classList.add('rail-drop-target');
  });
  rail.addEventListener('pointerup',event=>{
    if(!gesture||event.pointerId!==gesture.id) return;
    const {button,target,active}=gesture;
    release();
    if(active){
      event.preventDefault();suppressUntil=Date.now()+400;
      if(target&&target!==button) _moveTabOrderPanel(orderKey(button),orderKey(target));
      button.focus({preventScroll:true});
    }
  });
  function cancel(event){
    if(gesture&&(!event||event.pointerId===gesture.id)){
      if(gesture.active) suppressUntil=Date.now()+400;
      release();
    }
  }
  rail.addEventListener('pointercancel',cancel);
  rail.addEventListener('lostpointercapture',cancel);
  // Pointerup outside the rail must not leave a pending long-press timer.
  document.addEventListener('pointerup',cancel);
  rail.addEventListener('click',event=>{
    if(movable(event.target)&&(editing||Date.now()<suppressUntil)){
      event.preventDefault();event.stopImmediatePropagation();
    }
  },true);
  rail.addEventListener('contextmenu',event=>{if(editing||gesture){event.preventDefault();}});
  document.addEventListener('pointerdown',event=>{if(!rail.contains(event.target))finish();},true);
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'){if(editing||gesture){event.preventDefault();finish();}return;}
    const button=movable(event.target);
    if(!button||button.closest('.rail')!==rail) return;
    if(event.altKey&&['ArrowUp','ArrowDown'].includes(event.key)){
      event.preventDefault();edit();
      const nodes=Array.from(rail.querySelectorAll(selector)).filter(node=>!node.classList.contains('nav-tab-hidden'));
      const target=nodes[nodes.indexOf(button)+(event.key==='ArrowUp'?-1:1)];
      if(target) _moveTabOrderPanel(orderKey(button),orderKey(target));
      button.focus({preventScroll:true});
    }
  });
  window.addEventListener('blur',finish);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)finish();});
})();
