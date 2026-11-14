'use strict';

document.querySelector('#config').addEventListener('submit', async event => {
 event.preventDefault();
 const form=event.currentTarget, data=Object.fromEntries(new FormData(form).entries());
 data.one_pr=!!form.elements.one_pr.checked;
 const status=document.querySelector('#status'); status.textContent='Generation...';
 try {
  const response=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(!response.ok) throw new Error(await response.text());
  const blob=await response.blob(), url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url; link.download=data.name+'.zip'; link.click(); URL.revokeObjectURL(url);
  status.textContent='Archive generee.';
 } catch(error) {status.textContent='Erreur : '+error.message;}
});
