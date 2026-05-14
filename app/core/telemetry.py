import os
import json
import logging
import random
from typing import Sequence
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from app.core.config import settings

logger = logging.getLogger(__name__)

class JSONLFileExporter(SpanExporter):
    """
    Exports OTel Spans to a deterministic, offline-inspectable rotating JSONL file.
    Follows Phase A architectural constraints.
    """
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.file_path = os.path.join(self.log_dir, "traces.jsonl")

    def export(self, spans: Sequence[trace.Span]) -> SpanExportResult:
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                for span in spans:
                    span_data = {
                        "trace_id": format(span.context.trace_id, '032x'),
                        "span_id": format(span.context.span_id, '016x'),
                        "parent_id": format(span.parent.span_id, '016x') if span.parent else None,
                        "name": span.name,
                        "start_time": span.start_time,
                        "end_time": span.end_time,
                        "duration_ms": (span.end_time - span.start_time) / 1e6 if span.end_time else 0,
                        "status": span.status.status_code.name if span.status else "UNSET",
                        "attributes": dict(span.attributes) if span.attributes else {},
                        "events": [{"name": e.name, "timestamp": e.timestamp, "attributes": dict(e.attributes)} for e in span.events]
                    }
                    f.write(json.dumps(span_data) + "\n")
            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export traces: {e}")
            return SpanExportResult.FAILURE

    def shutdown(self):
        pass

class AdaptiveSampler(trace.sampling.Sampler):
    """
    Do NOT store every full trace forever.
    Adaptive sampling: Always store failures, CAPTCHA, selector degradation.
    Sample successful applies probabilistically.
    """
    def __init__(self, success_sample_rate: float = 0.1):
        self.success_sample_rate = success_sample_rate

    def should_sample(
        self,
        parent_context,
        trace_id,
        name,
        kind,
        attributes,
        links,
        trace_state,
    ) -> trace.sampling.SamplingResult:
        
        # Heuristics for forced sampling based on attributes/name
        force_sample = False
        if attributes:
            if attributes.get("error") == True:
                force_sample = True
            if "captcha" in name.lower() or attributes.get("captcha_detected") == True:
                force_sample = True
            if attributes.get("selector_degraded") == True:
                force_sample = True

        if force_sample:
            return trace.sampling.SamplingResult(trace.sampling.Decision.RECORD_AND_SAMPLE)

        # Probabilistic for the rest
        if random.random() < self.success_sample_rate:
            return trace.sampling.SamplingResult(trace.sampling.Decision.RECORD_AND_SAMPLE)
            
        return trace.sampling.SamplingResult(trace.sampling.Decision.DROP)

    def get_description(self) -> str:
        return "CareerOSAdaptiveSampler"

def setup_telemetry():
    """Initializes OpenTelemetry with the local JSONL exporter and adaptive sampling."""
    resource = Resource(attributes={"service.name": "careeros-orchestrator"})
    
    # Use our custom sampler
    sampler = AdaptiveSampler(success_sample_rate=0.2)
    provider = TracerProvider(resource=resource, sampler=sampler)
    
    # Phase A: Local JSONL rotating exporter
    otel_dir = os.path.join(settings.TRACE_DIR, "otel")
    exporter = JSONLFileExporter(log_dir=otel_dir)
    
    # Batch processor for performance
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry configured with JSONL export and Adaptive Sampling.")
    
    return trace.get_tracer(__name__)

tracer = trace.get_tracer(__name__)
