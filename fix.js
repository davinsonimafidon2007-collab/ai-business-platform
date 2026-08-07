import { readFileSync, writeFileSync } from 'fs'; 
const isCRLF = readFileSync('frontend/src/app/admin/page.tsx','utf8').includes('\r\n'); 
let c = readFileSync('frontend/src/app/admin/page.tsx','utf8').replace(/\r\n/g,'\n'); 
