from scripts import benchmark_captura as benchmark


def _pipeline_result():
    return {
        "processing_metadata": {
            "provider_detected": "LITORAL_GAS",
            "engine": "RapidOCR-ONNX-PP-OCRv3",
            "timings": {"ocr_det_s": 0.1, "ocr_rec_s": 0.2, "total_s": 0.4},
        },
        "raw_ocr_text": "Litoral Gas\nCliente 12345678\nPeriodo 13/2026",
        "structured_output": {
            "document_type": "LITORAL_GAS_BILL",
            "candidate_fields": {
                "provider": "LITORAL_GAS",
                "cliente": "12345678",
                "periodo": "13/2026",
            },
            "validated_fields": {
                "provider": "LITORAL_GAS",
                "service": "GAS",
                "cliente": "12345678",
            },
            "rejected_fields": {
                "periodo": {"value": "13/2026", "reason": "month_out_of_range"},
            },
            "missing_fields": {
                "total": None,
            },
        },
    }


def test_parse_args_accepts_precision_report_outputs():
    args = benchmark.parse_args(
        [
            "--docs",
            "400",
            "--dataset",
            "synthetic",
            "--out",
            "_bench/precision.json",
            "--report-md",
            "_bench/precision.md",
        ]
    )

    assert args.docs == 400
    assert args.dataset == "synthetic"
    assert args.out == "_bench/precision.json"
    assert args.report_md == "_bench/precision.md"


def test_evaluate_document_result_differentiates_validated_rejected_and_missing(tmp_path):
    image_path = tmp_path / "doc.jpg"
    image_path.write_bytes(b"fake")
    case = {
        "id": "doc-1",
        "dataset_kind": "synthetic",
        "image_path": image_path,
        "provider": "LITORAL_GAS",
        "service": "GAS",
        "document_type": "LITORAL_GAS_BILL",
        "fields": {
            "provider": "LITORAL_GAS",
            "cliente": "12345678",
            "total": 100.0,
        },
        "must_reject_fields": ["periodo"],
    }

    result = benchmark.evaluate_document_result(case, _pipeline_result(), elapsed_s=0.42)

    assert result["raw_ocr_text"].startswith("Litoral Gas")
    assert result["candidate_fields"]["periodo"] == "13/2026"
    assert result["validated_fields"]["cliente"] == "12345678"
    assert result["rejected_fields"]["periodo"]["reason"] == "month_out_of_range"
    assert result["field_results"]["cliente"]["status"] == "validated_match"
    assert result["field_results"]["periodo"]["status"] == "rejected_expected"
    assert result["field_results"]["total"]["status"] == "missing_unexpected"
    assert result["false_positives_avoided"] == [
        {
            "field": "periodo",
            "candidate_value": "13/2026",
            "reason": "month_out_of_range",
            "validation_applied": "semantic_field_validator",
        }
    ]


def test_aggregate_results_groups_by_provider_service_and_field(tmp_path):
    image_path = tmp_path / "doc.jpg"
    image_path.write_bytes(b"fake")
    case = {
        "id": "doc-1",
        "dataset_kind": "synthetic",
        "image_path": image_path,
        "provider": "LITORAL_GAS",
        "service": "GAS",
        "document_type": "LITORAL_GAS_BILL",
        "fields": {"provider": "LITORAL_GAS", "cliente": "12345678", "total": 100.0},
        "must_reject_fields": ["periodo"],
    }
    doc_result = benchmark.evaluate_document_result(case, _pipeline_result(), elapsed_s=0.42)

    report = benchmark.aggregate_results([doc_result], cold_start_s=0.1, dataset_kind="synthetic")

    summary = report["summary"]
    assert summary["docs"] == 1
    assert summary["cold_start_s"] == 0.1
    assert summary["hot_p50_s"] == 0.42
    assert summary["process_rss_mb"] is None or summary["process_rss_mb"] > 0
    assert summary["provider_service"]["LITORAL_GAS/GAS"]["provider_matches"] == 1
    assert summary["provider_service"]["LITORAL_GAS/GAS"]["fields"]["cliente"]["validated_match"] == 1
    assert summary["provider_service"]["LITORAL_GAS/GAS"]["fields"]["periodo"]["rejected_expected"] == 1
    assert summary["fields"]["total"]["missing_unexpected"] == 1
    assert summary["false_positives_avoided_count"] == 1


def test_render_markdown_report_includes_false_positives():
    report = {
        "summary": {
            "dataset": "synthetic",
            "dataset_note": None,
            "docs": 1,
            "cold_start_s": None,
            "hot_p50_s": 0.1,
            "hot_p95_s": 0.1,
            "hot_mean_s": 0.1,
            "hot_max_s": 0.1,
            "docs_per_minute": 600,
            "process_rss_mb": 100,
            "false_positives_avoided_count": 1,
            "thresholds": {"hot_p95_s": 5.0, "hot_p95_status": "pass"},
            "provider_service": {
                "LITORAL_GAS/GAS": {
                    "documents": 1,
                    "provider_matches": 1,
                    "service_matches": 1,
                    "errors": 0,
                    "false_positives_avoided": 1,
                    "fields": {"periodo": {"rejected_expected": 1}},
                }
            },
        },
        "documents": [
            {
                "id": "doc-1",
                "false_positives_avoided": [
                    {
                        "field": "periodo",
                        "candidate_value": "13/2026",
                        "reason": "month_out_of_range",
                        "validation_applied": "semantic_field_validator",
                    }
                ],
            }
        ],
    }

    markdown = benchmark.render_markdown_report(report)

    assert "# Benchmark Precision OCR" in markdown
    assert "Falsos positivos evitados: 1" in markdown
    assert "`doc-1` campo `periodo` valor `13/2026`" in markdown
