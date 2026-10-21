/* 比较窗口只用于筛选和日历，不把月/年精度回写成某一天。 */
export function dateWindow(record){
  const precision=record.datePrecision;if(precision==='unknown'||!record.eventDate)return null;
  const parts=value=>{const match=/^([+-]?[0-9]+)(?:-([0-9]{2}))?(?:-([0-9]{2}))?$/.exec(value||'');return match?[Number(match[1]),Number(match[2]||1),Number(match[3]||1)]:null;};
  const from=parts(record.eventDate);if(!from)return null;let through=from;
  if(precision==='year')through=[from[0],12,31];
  if(precision==='month'){const [year,month]=from,leap=year%4===0&&(year%100!==0||year%400===0);through=[year,month,[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]];}
  if(precision==='range')through=parts(record.eventEndAt);
  return through?{from,through}:null;
}
const compare=(a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2];
export function onDay(record,key){if(!['day','range'].includes(record.datePrecision))return false;const window=dateWindow(record),date=key.split('-').map(Number);return !!window&&compare(window.from,date)<=0&&compare(window.through,date)>=0;}
export function inMonth(record,year,month){const window=dateWindow(record);return !!window&&compare(window.from,[year,month,31])<=0&&compare(window.through,[year,month,1])>=0;}
