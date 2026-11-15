import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:60000,workers:1,use:{baseURL:process.env.PAYOPS_UI_URL||'http://127.0.0.1:5173',headless:true,viewport:{width:1440,height:1000}},reporter:'list'});
