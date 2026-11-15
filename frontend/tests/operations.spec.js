import {test,expect} from '@playwright/test';
test('money flow searches an actual synthetic transaction',async({page})=>{
 await page.goto('/');
 const transactions=await (await page.request.get('/api/transactions')).json();
 await page.getByRole('navigation').getByRole('button',{name:'Money Flow',exact:true}).click();
 await page.getByLabel('Transaction ID',{exact:true}).fill(transactions[0].id);
 const result=page.waitForResponse(r=>r.url().includes('/api/money-flow/'+transactions[0].id));
 await page.getByRole('button',{name:'Track money flow'}).click();
 expect((await result).status()).toBe(200);
 await expect(page.getByRole('cell',{name:'AUTHORIZATION',exact:true})).toBeVisible();
 await expect(page.getByRole('cell',{name:'CLEARING',exact:true})).toBeVisible();
});
test('profit rankings show ledger reasons and fee audit works',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'Profit & Margin',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Synthetic profit and margin intelligence'})).toBeVisible();
 await page.getByRole('button',{name:'by rail',exact:true}).click();
 await expect(page.getByRole('cell',{name:'UPI',exact:true}).first()).toBeVisible();
 await page.getByRole('button',{name:'Run fee audit'}).click();
 await expect(page.getByText('Synthetic fee audit completed; recommendations are in Review Queue.')).toBeVisible();
});
test('impact shows assumptions beside computed synthetic values',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'Rupee Impact',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Synthetic rupee impact and assumptions'})).toBeVisible();
 await expect(page.getByText('Resolved amounts require synthetic recovery ledger entries; approvals alone never count.')).toBeVisible();
});
test('live incident creates real synthetic cases',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'Live Incidents',exact:true}).click();
 await page.getByRole('button',{name:'upi bank outage',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Synthetic incident processed: upi-bank-outage.'})).toBeVisible({timeout:60000});
});
test('what-if slider shows a read-only measured curve',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'What-if Autonomy',exact:true}).click();
 const slider=page.getByRole('slider');await slider.fill('0.80');
 await expect(page.getByRole('img',{name:'Synthetic autonomy versus human review curve'})).toBeVisible({timeout:60000});
 await expect(page.getByText(/Restricted actions remain human-only at every threshold/)).toBeVisible();
});
test('BIN and routing advice remain human-only',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'BIN & Routing',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Synthetic BIN and issuer intelligence'})).toBeVisible();
 await page.getByRole('button',{name:'Queue routing suggestions'}).click();
 await expect(page.getByRole('status').filter({hasText:'Human approval is required; no route changed.'})).toBeVisible();
});
test('earned autonomy displays measured quality and approved-only changes',async({page})=>{
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'Earned Autonomy',exact:true}).click();
 await page.getByRole('button',{name:'Assess measured quality'}).click();
 await expect(page.getByRole('status').filter({hasText:'Approve proposals in Review Queue.'})).toBeVisible({timeout:60000});
 await expect(page.getByText(/No automatic increase in autonomy/).first()).toBeVisible();
});
