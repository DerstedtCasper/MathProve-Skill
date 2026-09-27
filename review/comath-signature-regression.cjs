// Pass a compiled statement-signature module as argv[2]; no Lean invocation.
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
const cases = [
 ['plain','t','t : True','ok'],
 ['apostrophe',"t'","t' : True",'ok'],
 ['Greek','α','α : True','ok'],
 ['subscript','t₀','t₀ : True','ok'],
 ['qualified Unicode','A.α','A.α : True','ok'],
 ['name collision','t',"t' : True",'missing'],
 ['namespace collision','t','t.other : True','missing'],
 ['underscore collision','t','t_other : True','missing'],
 ['longer name','t','tt : True','missing'],
 ['universe','id','id.{u} {α : Sort u} (a : α) : α','ok'],
 ['no space before colon','t','t: True','ok'],
 ['duplicate signature','t','t : True\nt : True','ok'],
 ['ambiguous','t','t : True\nt : False','ambiguous'],
];
(async()=>{
 if(!process.argv[2])throw new Error('Usage: node comath-signature-regression.cjs PATH_TO_COMPILED_JS');
 const m = await import(pathToFileURL(path.resolve(process.argv[2])).href);
 const results = cases.map(([name,theorem_name,lean_check_output,expected])=>{
  const observed=m.extractLeanStatementSignature({theorem_name,lean_check_output}).result;
  return {name,expected,observed,pass:observed===expected};
 });
 console.log(JSON.stringify({scope:'standalone original/patched module, not full CoMath build or Lean replay',results},null,2));
 assert.equal(results.filter(r=>!r.pass).length,0,'signature regressions failed');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
