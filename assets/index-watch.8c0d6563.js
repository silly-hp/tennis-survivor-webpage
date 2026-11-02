(function(){
  var el=document.getElementById('watchCount'); if(!el) return;
  var n=0;
  try{
    var s=JSON.parse(localStorage.getItem('ts.watch.v1')||'null'), seen={};
    (s&&s.lists||[]).forEach(function(l){ (l.users||[]).forEach(function(u){ if(!seen[u]){ seen[u]=1; n++; } }); });
  }catch(e){}
  if(n){ el.textContent=n; el.hidden=false; el.parentNode.setAttribute('aria-label','我的关注 · '+n+' 人'); }
})();