import React,{useEffect,useState} from 'react';

export const operationsPages=['Money Flow'];
export async function opsApi(path,body){const r=await fetch('/api'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(typeof v.detail==='string'?v.detail:JSON.stringify(v.detail));return v}
export const rupees=p=>p===null||p===undefined?'Not observed':`${new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(p/100)} (synthetic)`;
export function OpsTable({rows}){if(!rows?.length)return <p className="tower-empty">No synthetic observations yet.</p>;const keys=Object.keys(rows[0]);return <div className="tower-table-scroll"><table className="tower-table"><thead><tr>{keys.map(k=><th key={k}>{k.replaceAll('_',' ')} · synthetic</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{keys.map(k=><td key={k}>{r[k]===null?'Not observed':typeof r[k]==='object'?JSON.stringify(r[k]):String(r[k])}</td>)}</tr>)}</tbody></table></div>}
export function OpsCard({title,children}){return <section className="tower-card"><header><h2>{title}</h2><small className="tower-fine">All figures synthetic</small></header><div style={{padding:20}}>{children}</div></section>}
export default function OperationsViews({page}){
 const [summary,setSummary]=useState(null),[id,setId]=useState(''),[result,setResult]=useState(null),[error,setError]=useState('');
 useEffect(()=>{if(page==='Money Flow')opsApi('/money-flow/summary').then(setSummary).catch(e=>setError(e.message))},[page]);
 async function lookup(e){e.preventDefault();setError('');try{setResult(await opsApi('/money-flow/'+encodeURIComponent(id)))}catch(e){setError(e.message)}}
 if(page!=='Money Flow')return null;
 return <><OpsCard title="Synthetic transaction lifecycle"><form className="tower-form" onSubmit={lookup}><label>Transaction ID<input required value={id} onChange={e=>setId(e.target.value)} placeholder="Copy a synthetic transaction ID from Transactions"/></label><button className="button primary">Track money flow</button></form>{error&&<p role="alert">{error}</p>}{result&&<><p>{result.likely_cause}: fee-adjusted gap {rupees(result.clearing_settlement_gap_paise)}</p><p className="tower-fine">{result.note}</p><OpsTable rows={result.stages}/></>}</OpsCard>{summary&&<><OpsCard title="Synthetic value between stages"><p>Pending exposure {rupees(summary.stuck_paise)}. Excess settlements {rupees(summary.excess_settlement_paise)}.</p><p>{summary.note}</p><OpsTable rows={summary.by_rail}/></OpsCard><OpsCard title="Synthetic exposure by merchant"><OpsTable rows={summary.by_merchant}/></OpsCard></>}</>
}
