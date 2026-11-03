/* Sporting Pearls - boys-programme.js (verbatim v15) */
document.documentElement.classList.add('js');
var prog=document.getElementById('progress');
var heroBg=document.getElementById('heroBg');
var ticking=false;

window.addEventListener('scroll',function(){
  if(!ticking){
    window.requestAnimationFrame(function(){
      var h=document.documentElement;
      prog.style.width=(window.scrollY/(h.scrollHeight-window.innerHeight)*100)+'%';
      if(heroBg)heroBg.style.transform='translateY('+(window.scrollY*0.25)+'px)';
      ticking=false;
    });
    ticking=true;
  }
},{passive:true});

/* IntersectionObserver for scroll reveals */
var io=new IntersectionObserver(function(entries){
  entries.forEach(function(e){
    if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}
  });
},{threshold:0,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('[data-reveal],.lines-t').forEach(function(el){io.observe(el);});
