"""Scientific repair behavior retained after retiring the historical rechipper."""

import numpy as np

from kelpseg.prepare.alignment import audit_label_block, repair_label_block


def test_repair_changes_only_image_nodata_and_missing_annotation():
    labels = np.array([[2, 1, 0], [3, 4, 0]], dtype=np.uint8)
    image_nodata = np.array([[True, False, False], [False, False, False]])
    coverage = np.array([[True, True, True], [True, False, True]])
    original = labels.copy()
    repaired = repair_label_block(labels, image_nodata, coverage)
    np.testing.assert_array_equal(repaired, [[3, 1, 0], [3, 3, 0]])
    np.testing.assert_array_equal(labels, original)
    assert repaired.dtype == np.uint8
    # Existing ignore over valid imagery remains; valid background stays zero.
    assert repaired[1, 0] == 3 and repaired[0, 2] == 0


def test_audit_counts_every_nodata_ignore_combination():
    image_nodata = np.array([[True, True], [False, False]])
    labels = np.array([[3, 0], [3, 1]], dtype=np.uint8)
    assert audit_label_block(image_nodata, labels) == {
        "total": 4,
        "image_nodata": 2,
        "tp": 1,
        "fp": 1,
        "fn": 1,
        "tn": 1,
    }
