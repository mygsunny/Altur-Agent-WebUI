"""Interactive intent tuning must not change provider/model or update summaries."""
import contextlib
import sys
import types
import pytest

def test_model_json_and_schema_failures_have_separate_safe_stages(monkeypatch):
 import api.cowork as cowork
 import api.routes as routes
 body={'document_id':'d','utterance_id':'u','text':'synthetic','context':{'kind':'document'}}
 for answer,stage in [('not JSON','model-json'),('{"document_id":"wrong"}','model-schema')]:
  monkeypatch.setattr(routes,'_llm_update_summary',lambda *a,**k:answer)
  with pytest.raises(cowork.ModelResponseError) as failure:cowork.infer_intent(body,'default')
  assert str(failure.value)==stage

def test_http_request_and_model_failures_do_not_share_status_or_leak_content(tmp_path,monkeypatch):
 import api.cowork as cowork
 import api.config as cfg
 import api.profiles as profiles
 import api.helpers as helpers
 import api.routes as routes
 from urllib.parse import urlparse
 monkeypatch.setattr(cfg,'STATE_DIR',str(tmp_path));monkeypatch.setattr(profiles,'get_active_profile_name',lambda:'default')
 monkeypatch.setattr(helpers,'bad',lambda handler,message,status=400:(status,message))
 cowork.SnapshotStore(tmp_path/'cowork').claim('default','d','browser')
 body={'profile':'default','owner':'browser','document_id':'d','utterance_id':'u','text':'PRIVATE_SYNTHETIC_TEXT','context':{'kind':'document'}}
 monkeypatch.setattr(routes,'_llm_update_summary',lambda *a,**k:'PRIVATE_SYNTHETIC_TEXT')
 status,message=cowork.handle(None,urlparse('/api/cowork/intent'),body);assert status==502 and 'model-json' in message and body['text'] not in message
 status,message=cowork.handle(None,urlparse('/api/cowork/intent'),{**body,'text':None});assert status==400 and 'request-validation' in message


def test_clear_content_is_one_bounded_operation():
 from api.cowork import validate_intent
 payload={'document_id':'d','utterance_id':'u','operations':[{'type':'sheet.clear','sheet_id':'sheet1','range':'A1:CV1000'}],'clarification':None}
 assert validate_intent(payload,'d','u')==payload
 payload['operations'][0]['code']='unsafe'
 with pytest.raises(ValueError):validate_intent(payload,'d','u')

@pytest.mark.parametrize('interactive,model,url,expected',[(True,'gpt-oss:20b','http://127.0.0.1:11435/v1',{'reasoning_effort':'low'}),(False,'gpt-oss:20b','http://127.0.0.1:11435/v1',{}),(True,'other','http://127.0.0.1:11435/v1',{}),(True,'gpt-oss:20b','https://example.test/v1',{})])
def test_interactive_local_intent_uses_low_reasoning_without_rerouting(monkeypatch,interactive,model,url,expected):
 import api.routes as routes
 import api.config as cfg
 import api.profiles as profiles
 calls=[]
 monkeypatch.setattr(profiles,'profile_env_for_background_worker',lambda *a,**k:contextlib.nullcontext())
 monkeypatch.setattr(cfg,'get_effective_default_model',lambda:model)
 monkeypatch.setattr(cfg,'resolve_model_provider',lambda m:(m,'custom',url))
 monkeypatch.setattr(routes,'_resolve_agent_connection_bundle',lambda *a:{'provider':'custom','api_key':'synthetic','base_url':url})
 monkeypatch.setattr(routes,'_auxiliary_main_runtime',lambda b,m:{'provider':'custom','model':m,'base_url':url})
 monkeypatch.setattr(routes,'ensure_agent_runtime_current',lambda:None)
 def create(**kwargs):
  calls.append(kwargs);return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{}'))])
 client=types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
 fake=types.ModuleType('agent.auxiliary_client');fake.get_text_auxiliary_client=lambda *a,**k:(client,model)
 monkeypatch.setitem(sys.modules,'agent.auxiliary_client',fake)
 assert routes._llm_update_summary('system','user',active_profile='default',interactive_intent=interactive)=='{}'
 assert calls==[{'model':model,'messages':[{'role':'system','content':'system'},{'role':'user','content':'user'}],**expected}]
