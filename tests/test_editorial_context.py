from app.services.document_generation_v2 import DocumentGenerationV2


def test_document_prompts_keep_full_evidence_and_shared_preferences():
    master = {'evidence': 'x' * 25000, 'last_proof': 'FINAL_VERIFIED_PROOF'}
    for builder in (DocumentGenerationV2._cv_prompt, DocumentGenerationV2._letter_prompt):
        prompt = builder({'job_title': 'Analyst'}, master)
        assert 'FINAL_VERIFIED_PROOF' in prompt
        assert 'Ne jamais inventer' in prompt
        assert 'minimum salarial' in prompt
