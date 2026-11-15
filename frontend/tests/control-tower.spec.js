import {test,expect} from '@playwright/test';

test('simulator, chargeback review, feedback, audit and original dispute workflow',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Payment operations, in focus.'})).toBeVisible();
  await page.getByLabel('Batch size').fill('32');
  await page.getByLabel('Seed',{exact:true}).fill('884');
  await page.getByRole('button',{name:'Start synthetic batch'}).click();
  await expect(page.getByRole('button',{name:'Start synthetic batch'})).toBeEnabled({timeout:60000});
  await page.getByRole('navigation').getByRole('button',{name:'Disputes',exact:true}).click();
  await page.getByRole('row').filter({hasText:'OPEN'}).first().getByRole('button',{name:/^Open DIS-/}).click();
  const dialog=page.getByRole('dialog');
  await expect(dialog.getByRole('heading',{name:'Dispute evidence checklist'})).toBeVisible();
  await expect(dialog.getByText('signed receipt',{exact:true})).toBeVisible();
  await dialog.getByLabel('Review comment / correction reason').fill('Synthetic browser review completed');
  await dialog.getByRole('button',{name:'Approve recommendation',exact:true}).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:'Review Queue'}).click();
  const open=page.getByRole('row').filter({hasText:'OPEN'}).first();
  await open.getByRole('button',{name:/^Open /}).click();
  await dialog.getByLabel('Review comment / correction reason').fill('Synthetic analyst override for calibration');
  await dialog.getByLabel('Corrected action').selectOption('NO_ACTION');
  await dialog.getByRole('button',{name:'Save correction'}).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole('button',{name:'Recalibrate from feedback'}).click();
  await expect(page.getByRole('heading',{name:'Feedback calibration'})).toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:'Audit Trail'}).click();
  await expect(page.getByText(/chained events · integrity verified/)).toBeVisible();
  await expect(page.getByText(/HUMAN APPROVE/).first()).toBeVisible();
  await page.getByRole('navigation').getByRole('button',{name:'Disputes',exact:true}).click();
  await page.getByRole('button',{name:'Open original notice workflow'}).click();
  await page.getByRole('button',{name:'Run agent',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Every claim checked against the ledger'})).toBeVisible();
  await page.screenshot({path:'test-results/original-workflow.png',fullPage:true});
  expect(errors).toEqual([]);
});

test('mobile dashboard stays within viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');
  await expect(page.getByRole('heading',{name:'Payment operations, in focus.'})).toBeVisible();
  await expect(page.getByLabel('Batch size')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
  await page.screenshot({path:'test-results/mobile.png',fullPage:true});
});
