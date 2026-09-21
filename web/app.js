const $ = id => document.getElementById(id);
const palette = ['#337b65','#d5984c','#577ab7','#bc6a79','#8d70ae','#56aeb1','#a27d54','#82a356','#d480b3'];
const state = {points:[], topics:[], chosen:null, hovered:null, query:'', researcher:'', year:'', ids:null};
const canvas = $('map'), ctx = canvas.getContext('2d');
let visiblePoints = [], timer;
const fetchJSON = async path => {const response = await fetch(path);if(!response.ok)throw Error('Erreur de chargement');return response.json()};
const color = n => palette[n % palette.length];
const addText = (parent,tag,value,className) => {const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;parent.append(node);return node};

function fit(){
  const box=canvas.getBoundingClientRect(), pixelRatio=window.devicePixelRatio||1;
  canvas.width=Math.round(box.width*pixelRatio);canvas.height=Math.round(box.height*pixelRatio);
  ctx.setTransform(pixelRatio,0,0,pixelRatio,0,0);
  draw();
}
function draw(){
  const w=canvas.clientWidth,h=canvas.clientHeight;
  ctx.clearRect(0,0,w,h);visiblePoints=[];
  if(!state.points.length)return;
  const pts=state.points, xs=pts.map(p=>p.x).sort((a,b)=>a-b),ys=pts.map(p=>p.y).sort((a,b)=>a-b);
  const lowX=xs[Math.floor(xs.length*.015)],highX=xs[Math.floor(xs.length*.985)];
  const lowY=ys[Math.floor(ys.length*.015)],highY=ys[Math.floor(ys.length*.985)];
  const margin=30;
  for(const p of pts){
    if(state.chosen!==null&&p.cluster!==state.chosen)continue;
    if(state.researcher&&!p.researchers.includes(state.researcher))continue;
    if(state.year&&String(p.year)!==state.year)continue;
    const x=margin+Math.max(0,Math.min(1,(p.x-lowX)/(highX-lowX||1)))*(w-margin*2);
    const y=margin+Math.max(0,Math.min(1,(p.y-lowY)/(highY-lowY||1)))*(h-margin*2);
    const focus=state.ids?.has(p.id),active=p.id===state.hovered;
    ctx.beginPath();ctx.arc(x,y,active?6:focus?4:2.6,0,Math.PI*2);
    ctx.fillStyle=color(p.cluster);ctx.globalAlpha=state.ids?(focus ? .92 : .09):.45;ctx.fill();
    if(active){ctx.strokeStyle='#152a30';ctx.lineWidth=1.5;ctx.stroke()}
    visiblePoints.push({...p,px:x,py:y});
  }
  ctx.globalAlpha=1;
  $('map-count').textContent=visiblePoints.length.toLocaleString('fr-FR')+' points';
}
function showLegend(){
  const target=$('legend');target.replaceChildren();
  for(const topic of state.topics){
    const btn=document.createElement('button');btn.type='button';btn.className='chip'+(state.chosen===topic.id?' active':'');
    btn.title=topic.terms.join(' · ');const dot=document.createElement('span');dot.className='dot';dot.style.background=color(topic.id);btn.append(dot);
    addText(btn,'span',topic.name+' ('+topic.count+')');
    btn.onclick=()=>{state.chosen=state.chosen===topic.id?null:topic.id;showLegend();draw();search()};
    target.append(btn);
  }
}
function renderCards(data){
  $('result-count').textContent=data.total.toLocaleString('fr-FR')+' résultats';
  const target=$('cards');target.replaceChildren();
  if(!data.items.length){addText(target,'div','Aucune publication pour ces critères.','empty');return}
  for(const p of data.items){
    const card=document.createElement('article');card.className='card';card.dataset.id=p.id;
    const top=document.createElement('div');top.className='card-top';const dot=document.createElement('span');dot.className='dot';dot.style.background=color(p.cluster);top.append(dot);
    addText(top,'span',[(p.year||'Année inconnue'),p.journal].filter(Boolean).join(' · '));card.append(top);
    const h=addText(card,'h3','');
    if(p.url&&/^https?:\/\//i.test(p.url)){const a=document.createElement('a');a.href=p.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=p.title;h.append(a)}else h.textContent=p.title;
    addText(card,'p',p.abstract||'Résumé non disponible.');
    addText(card,'small',[p.authors.slice(0,3).join(', '),`${p.citations} citations`].filter(Boolean).join(' · '));
    card.onmouseenter=()=>{state.hovered=p.id;draw()};card.onmouseleave=()=>{state.hovered=null;draw()};target.append(card);
  }
}
let searchSeq=0;
async function search(){
  const seq=++searchSeq,params=new URLSearchParams({q:state.query,researcher:state.researcher,year:state.year,limit:40});
  if(state.chosen!==null)params.set('cluster',state.chosen);
  try{const result=await fetchJSON('/api/search?'+params);if(seq!==searchSeq)return;
    state.ids=state.query?new Set(result.items.map(p=>p.id)):null;
    renderCards(result);draw();
  }catch{if(seq===searchSeq)addText($('cards'),'div','Impossible de charger les résultats.','empty')}
}
canvas.addEventListener('mousemove',event=>{
  const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top;
  let found=null,best=100;
  for(const p of visiblePoints){const d=(p.px-x)**2+(p.py-y)**2;if(d<best){best=d;found=p}}
  const tip=$('tooltip');tip.hidden=!found;
  if(found){tip.textContent=found.title;tip.style.left=Math.max(5,Math.min(x+13,rect.width-285))+'px';tip.style.top=Math.max(5,y-43)+'px'}
  if(state.hovered!==found?.id){state.hovered=found?.id||null;draw()}
});
canvas.addEventListener('mouseleave',()=>{$('tooltip').hidden=true;state.hovered=null;draw()});
canvas.addEventListener('click',()=>{if(!state.hovered)return;
  const card=[...document.querySelectorAll('.card')].find(el=>el.dataset.id===state.hovered);
  if(card){card.scrollIntoView({behavior:'smooth',block:'nearest'});card.classList.add('focused');setTimeout(()=>card.classList.remove('focused'),1400)}
  else fetchJSON('/api/paper?id='+encodeURIComponent(state.hovered)).then(p=>{if(p.url&&/^https?:\/\//i.test(p.url))window.open(p.url,'_blank','noopener')});
});
$('query').oninput=e=>{state.query=e.target.value;clearTimeout(timer);timer=setTimeout(search,220)};
$('researcher').onchange=e=>{state.researcher=e.target.value;draw();search()};
$('year').onchange=e=>{state.year=e.target.value;draw();search()};
$('reset').onclick=()=>{state.query=state.researcher=state.year='';state.chosen=null;$('query').value=$('researcher').value=$('year').value='';showLegend();draw();search()};
window.addEventListener('resize',fit);
async function start(){try{
  const [summary,map]=await Promise.all([fetchJSON('/api/overview'),fetchJSON('/api/map')]);
  state.points=map.points;state.topics=summary.topics;
  $('count-papers').textContent=summary.papers.toLocaleString('fr-FR');$('count-people').textContent=summary.researchers;$('count-topics').textContent=summary.topics.length;
  for(const p of summary.people.sort((a,b)=>a.name.localeCompare(b.name))){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;$('researcher').append(o)}
  for(const y of summary.years.reverse()){const o=document.createElement('option');o.value=y.year;o.textContent=y.year+' ('+y.count+')';$('year').append(o)}
  showLegend();fit();search();
}catch{addText($('cards'),'div','Le jeu de données n’a pas pu être chargé.','empty')}}
start();
