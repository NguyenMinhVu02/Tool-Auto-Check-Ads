"""Validate claim structure and source references; this is not semantic proof.

A linked, exact excerpt does not establish that a call is reachable, that a gate
has a particular value, or that runtime behavior happened. FAIL also needs the
separate targeted AI review performed by agent.evaluate.
"""

VERIFIER_POLICY_VERSION = 'claims-3-ancillary-review'


def verify_claims(payload, checked_evidence):
    errors = []
    claims = payload.get('claims')
    definite = payload.get('status') in {'PASS', 'FAIL'}
    report = {'valid': False, 'level': 'structure_and_evidence', 'semantic_proof': False,
              'errors': errors, 'claims': []}
    if not isinstance(claims, list) or not claims:
        errors.append('missing_claims')
        return report
    identifiers = set()
    supported = []

    def refs_valid(refs):
        return (isinstance(refs, list) and bool(refs)
                and all(type(i) is int and 0 <= i < len(checked_evidence)
                        and checked_evidence[i].get('verified') is True for i in refs))

    for index, claim in enumerate(claims):
        problems = []
        if not isinstance(claim, dict):
            errors.append(f'claim[{index}]:invalid_object')
            continue
        ident = claim.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in identifiers:
            problems.append('invalid_id')
        else:
            identifiers.add(ident)
        if not isinstance(claim.get('statement'), str) or not claim['statement'].strip():
            problems.append('missing_statement')
        if claim.get('kind') not in ('compliance', 'violation', 'uncertain'):
            problems.append('invalid_kind')
        if claim.get('scope') not in ('static', 'runtime'):
            problems.append('invalid_scope')
        if claim.get('applicability') not in ('applicable', 'unknown', 'not_applicable'):
            problems.append('invalid_applicability')
        for field in ('conditions', 'unresolved'):
            value = claim.get(field)
            if not isinstance(value, list) or not all(isinstance(s, str) and s.strip() for s in value):
                problems.append('invalid_' + field)
        # Older stored/replay claims may lack this newly introduced field.
        # A stated limitation never suppresses an unresolved blocker.
        limitations = claim.get('limitations', [])
        if not isinstance(limitations, list) or not all(isinstance(s, str) and s.strip() for s in limitations):
            problems.append('invalid_limitations')
        refs = claim.get('evidence_indices')
        if not refs_valid(refs):
            problems.append('invalid_evidence_indices')
        path = claim.get('path')
        roles = set()
        if not isinstance(path, list):
            problems.append('missing_path')
        else:
            for step in path:
                if not isinstance(step, dict):
                    problems.append('invalid_path_step')
                    continue
                role = step.get('role')
                step_refs = step.get('evidence_indices')
                if not isinstance(role, str) or not role.strip():
                    problems.append('invalid_path_role')
                else:
                    roles.add(role.strip().casefold())
                if (not refs_valid(step_refs) or not isinstance(refs, list)
                        or any(i not in refs for i in step_refs)):
                    problems.append('invalid_path_evidence')
        relevant = claim.get('applicability') != 'not_applicable'
        if definite and relevant:
            if claim.get('scope') != 'static':
                problems.append('runtime_not_proven')
            if claim.get('applicability') != 'applicable':
                problems.append('applicability_not_proven')
            if claim.get('unresolved'):
                problems.append('unresolved_blocker')
            if claim.get('kind') == 'uncertain':
                problems.append('uncertain_claim')
            if len(roles) < 2:
                problems.append('incomplete_path')
        if not problems and relevant:
            supported.append(claim['kind'])
        report['claims'].append({'id': ident, 'kind': claim.get('kind'), 'valid': not problems, 'errors': problems,
                                 'supports_verdict': not problems and relevant})
        errors.extend(f'claim[{index}]:{problem}' for problem in problems)
    if definite:
        if payload['status'] == 'PASS' and ('compliance' not in supported or 'violation' in supported):
            errors.append('pass_claim_mismatch')
        if payload['status'] == 'FAIL' and 'violation' not in supported:
            errors.append('fail_without_violation')
    report['valid'] = not errors
    return report
