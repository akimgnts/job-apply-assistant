const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');

function fixture(){
  class Input{
    constructor(label,type='text',value=''){this.tagName='INPUT';this.name=label;this.labels=[{innerText:label}];this.type=type;this._value=value;this.events=[];}
    get value(){return this._value;}set value(v){this._value=v;}
    getClientRects(){return [1];}closest(){return null;}getAttribute(){return null;}
    dispatchEvent(e){this.events.push(e.type);}
  }
  const fields=[new Input('Email','email'),new Input('Prénom','text','Already here'),new Input('Password','password'),new Input('Agree','checkbox')];
  const context={document:{querySelectorAll:q=>q==='iframe'?[]:fields,querySelector:()=>({innerText:'Offer SQL'}),getElementById:()=>null,title:'Job'},location:{href:'https://jobs.example/apply'},HTMLInputElement:Input,HTMLTextAreaElement:Input,Event:class{constructor(type){this.type=type;}}};
  vm.createContext(context);vm.runInContext(readFileSync(__dirname+'/form.js','utf8'),context);
  return {agent:context.jobApplyForm,fields,context};
}
test('scan does not extract existing input values or submit controls',()=>{
  const {agent}=fixture();const scanned=agent.scan();
  assert.equal(scanned.fields[1].filled,true);
  assert.equal(JSON.stringify(scanned).includes('Already here'),false);
});
test('fill preserves existing values and personal agreements',()=>{
  const {agent,fields}=fixture();const scanned=agent.scan();
  const result=agent.apply(scanned.url,scanned.fields.map(f=>({id:f.id,value:'test@example.org'})));
  assert.equal(result.applied.length,1);
  assert.equal(fields[0].value,'test@example.org');
  assert.deepEqual(fields[0].events,['input','change']);
  assert.equal(fields[1].value,'Already here');assert.equal(fields[2].value,'');assert.equal(fields[3].value,'');
});
test('changed page or relabelled field cannot receive stale answers',()=>{
  const {agent,fields}=fixture();const scanned=agent.scan();
  assert.throws(()=>agent.apply('https://different.example',[]),/changé/);
  fields[0].labels=[{innerText:'Salary'}];
  assert.equal(agent.apply(scanned.url,[{id:scanned.fields[0].id,value:'test@example.org'}]).skipped.length,1);
});
