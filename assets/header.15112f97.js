(function(){
  const top=document.getElementById('toTop');
  if(top){
    const sync=()=>{top.hidden=window.scrollY<window.innerHeight;};
    window.addEventListener('scroll',sync,{passive:true});sync();
    top.addEventListener('click',()=>{
      const still=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({top:0,behavior:still?'auto':'smooth'});
    });
  }
  const cur=document.querySelector('.hd-tab[aria-current="page"]');
  if(cur&&cur.scrollIntoView)cur.parentNode.scrollLeft=cur.offsetLeft-24;
})();