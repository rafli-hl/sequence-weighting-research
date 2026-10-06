"""Mathematical and dataset checks that do not import any training runtime."""
import json
import math
from pathlib import Path
from core import exponent, make_data_lists


def main():
    weights = [math.exp(-3 + 6*i/99) for i in range(100)]
    recovered = []
    for expected in (0, .5, 1, 2):
        result = exponent(weights, [2*w**expected for w in weights])
        assert abs(result['p']-expected) < 1e-5
        recovered.append({'known_p': expected, 'estimated_p': result['p']})
    gains = [1+.3*math.sin(i) for i in range(100)]
    fit = exponent(weights, gains)
    norm = sum(w**fit['p'] for w in weights)
    d = [g/sum(gains)-w**fit['p']/norm for g,w in zip(gains,weights)]
    direct = sum(d[i]*min((i+1)/100,(j+1)/100)*d[j] for i in range(100) for j in range(100))
    assert abs(direct-fit['objective']) < 1e-12
    assert exponent([1,1], [1,2])['reason'] == 'constant_weights'
    assert exponent([1,2], [-1,0])['reason'] == 'nonpositive_total_gain'
    splits, meta = make_data_lists(1729, 'mixed', 2048, 256, 512)
    control, _ = make_data_lists(1729, 'shared', 2048, 256, 512)
    ids = meta['sequence_keys']
    assert len(ids) == len(set(ids)) == 2816
    for name, (rows,kinds) in splits.items():
        for row,mask,other in zip(rows,kinds,control[name][0]):
            assert len(row) == 41 and len(mask) == 40
            assert row[:5] == other[:5] and row[6::3] == other[6::3]
            assert len(set(row[6::3])) == 12
            assert all(mask.count(t) == 4 for t in range(3))
            for index,typ in enumerate(mask):
                if typ == 0:
                    assert row[index+1]-68 == (row[index]-52+1)%16
                elif typ == 1:
                    assert row[index+1]-68 == meta['group_permutations'][row[1]-1][row[index]-52]
                elif typ == 2:
                    assert 68 <= row[index+1] <= 83
    status = {
        'status': 'passed', 'known_exponent_recovery': recovered,
        'quadratic_form_equivalence_absolute_error': abs(direct-fit['objective']),
        'distinct_sequence_keys': len(ids),
        'checks': ['constant weight and nonpositive gain handling',
                   'all 2816 sequences: lengths, target alignment, pattern counts',
                   'shared and group answer correctness', 'unique inputs within each sequence',
                   'disjoint train/validation/test keys', 'cross-regime query pairing'],
        'not_checked': ['Transformer causality at runtime', 'CUDA training', 'learning curves',
                        'runtime performance or peak GPU memory'],
        'training_status': 'not performed by these dependency-free checks; inspect run outputs separately'
    }
    output = Path(__file__).with_name('CORE_CHECKS.json')
    output.write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
