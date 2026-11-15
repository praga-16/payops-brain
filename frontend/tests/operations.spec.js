import {test,expect} from '@playwright/test';
test('money flow searches an actual synthetic transaction',async({page})=>{
 await page.goto('/');
 const transactions=await (await page.request.get('/api/transactions')).json();
 await page.getByRole('navigation').getByRole('button',{name:'Money Flow',exact:true}).click();
 await page.getByLabel('Transaction ID',{exact:true}).fill(transactions[0].id);
 await page.getByRole('button',{name:'Track money flow'}).click();
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
