#!/usr/bin/env python3
"""Test that all prompts can be called without f-string ValueError.

Regression test for brace escaping in f-strings with JSON examples.
"""

import sys
sys.path.insert(0, '/Users/akimguentas/job-apply-assistant')


def test_gap_analysis_prompt():
    """Test gap analysis prompt f-string doesn't crash."""
    from app.prompts.gap_analysis_prompt import get_gap_analysis_prompt

    try:
        result = get_gap_analysis_prompt(
            {
                'company': 'Test Corp',
                'job_title': 'Data Engineer',
                'missions': ['Build pipelines', 'Optimize queries'],
                'required_skills': ['SQL', 'Python'],
                'soft_skills': ['Communication'],
                'analysis_summary': 'Test analysis',
            },
            'Data & AI Consultant',
            {},
        )
        assert isinstance(result, str)
        assert len(result) > 0
        print("✓ gap_analysis_prompt: OK")
        return True
    except ValueError as e:
        if "Invalid format specifier" in str(e):
            print(f"✗ gap_analysis_prompt: FAIL - f-string brace escaping: {e}")
            return False
        raise
    except Exception as e:
        print(f"✗ gap_analysis_prompt: {type(e).__name__}: {e}")
        return False


def test_letter_prompt():
    """Test letter prompt f-string doesn't crash."""
    from app.prompts.letter_prompt import get_letter_prompt

    try:
        result = get_letter_prompt(
            {
                'company': 'Test Corp',
                'job_title': 'Data Engineer',
                'missions': ['Build pipelines'],
            },
            'Data Engineer',
            {'confidence': 0.75, 'bridges': ['Data experience applies']},
            {},
        )
        assert isinstance(result, str)
        assert len(result) > 0
        print("✓ letter_prompt: OK")
        return True
    except ValueError as e:
        if "Invalid format specifier" in str(e):
            print(f"✗ letter_prompt: FAIL - f-string brace escaping: {e}")
            return False
        raise
    except Exception as e:
        print(f"✗ letter_prompt: {type(e).__name__}: {e}")
        return False


def test_positioning_prompt():
    """Test positioning prompt f-string doesn't crash."""
    from app.prompts.positioning_prompt import get_positioning_prompt

    try:
        result = get_positioning_prompt(
            {
                'company': 'Test Corp',
                'job_title': 'Data Engineer',
                'required_skills': ['SQL', 'Python'],
                'missions': ['Build pipelines'],
                'analysis_summary': 'Test',
            }
        )
        assert isinstance(result, str)
        assert len(result) > 0
        print("✓ positioning_prompt: OK")
        return True
    except ValueError as e:
        if "Invalid format specifier" in str(e):
            print(f"✗ positioning_prompt: FAIL - f-string brace escaping: {e}")
            return False
        raise
    except Exception as e:
        print(f"✗ positioning_prompt: {type(e).__name__}: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing prompt f-string escaping...")
    print()

    tests = [
        test_gap_analysis_prompt,
        test_letter_prompt,
        test_positioning_prompt,
    ]

    results = [test() for test in tests]

    print()
    print(f"Results: {sum(results)}/{len(results)} passed")

    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
