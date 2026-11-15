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
