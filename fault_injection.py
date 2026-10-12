from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class ClockFaultConfig:
    rate_hz: float
    jitter_std_us: float = 0.0
    drift_ppm: float = 0.0
    drop_probability: float = 0.0
    duplicate_probability: float = 0.0
    reset_at_s: float | None = None
    reset_jump_ms: float = 0.0


@dataclass(slots=True)
class TactileFaultConfig:
    channels: int = 160
    noise_std: float = 0.05
    negative_drift_per_s: float = 0.0
    stuck_channel: int | None = None
    disconnect_start_s: float | None = None
    disconnect_duration_s: float = 0.0


def simulate_clock(duration_s: float, cfg: ClockFaultConfig, seed: int = 0) -> dict[str, np.ndarray]:
    if duration_s <= 0 or cfg.rate_hz <= 0: raise ValueError("duration/rate must be positive")
    rng=np.random.default_rng(seed)
    n=int(np.floor(duration_s*cfg.rate_hz))
    ideal=np.arange(n,dtype=np.float64)*(1e9/cfg.rate_hz)
    source=ideal*(1.0+cfg.drift_ppm*1e-6)
    if cfg.jitter_std_us:
        source += rng.normal(0,cfg.jitter_std_us*1e3,n)
    if cfg.reset_at_s is not None:
        source[ideal >= cfg.reset_at_s*1e9] += cfg.reset_jump_ms*1e6
    keep=rng.random(n) >= cfg.drop_probability
    seq=np.arange(n,dtype=np.int64)[keep]
    src=np.rint(source[keep]).astype(np.int64)
    global_ns=np.rint(ideal[keep]).astype(np.int64)
    if cfg.duplicate_probability > 0 and len(seq):
        dup=rng.random(len(seq)) < cfg.duplicate_probability
        seq=np.repeat(seq,1+dup.astype(np.int64))
        src=np.repeat(src,1+dup.astype(np.int64))
        global_ns=np.repeat(global_ns,1+dup.astype(np.int64))
    return {"sample_seq":seq,"source_timestamp_ns":src,"global_timestamp_ns":global_ns}


def simulate_tactile(duration_s: float, rate_hz: float, cfg: TactileFaultConfig = TactileFaultConfig(), seed: int = 1) -> dict[str,np.ndarray]:
    rng=np.random.default_rng(seed)
    n=int(np.floor(duration_s*rate_hz)); t=np.arange(n,dtype=np.float64)/rate_hz
    x=rng.normal(0,cfg.noise_std,(n,cfg.channels)).astype(np.float32)
    if cfg.negative_drift_per_s:
        x += (-cfg.negative_drift_per_s*t[:,None]).astype(np.float32)
    # deterministic contact pulse, useful for regression tests
    on=(t>=duration_s*0.35)&(t<duration_s*0.65)
    if np.any(on): x[on,0:4] += 3.0
    valid=np.ones(n,dtype=bool)
    if cfg.disconnect_start_s is not None:
        bad=(t>=cfg.disconnect_start_s)&(t<cfg.disconnect_start_s+cfg.disconnect_duration_s)
        x[bad]=np.nan; valid[bad]=False
    if cfg.stuck_channel is not None:
        x[:,cfg.stuck_channel]=0.123
    return {"time_s":t.astype(np.float32),"values":x,"valid":valid}


def simulate_virtual_stack(duration_s: float = 10.0, *, seed: int = 7) -> dict:
    """Generate deterministic virtual OGLO/OVision/IMU timing streams with faults off."""
    return {
        "camera": simulate_clock(duration_s, ClockFaultConfig(60.0,jitter_std_us=20), seed),
        "tactile": simulate_clock(duration_s, ClockFaultConfig(300.0,jitter_std_us=15), seed+1),
        "imu": simulate_clock(duration_s, ClockFaultConfig(400.0,jitter_std_us=10), seed+2),
        "tactile_values": simulate_tactile(duration_s,300.0,seed=seed+3),
    }

@dataclass(slots=True)
class AudioFaultConfig:
    sample_rate_hz: int = 48_000
    channels: int = 1
    noise_std: float = 0.01
    tone_hz: float = 440.0
    dropout_start_s: float | None = None
    dropout_duration_s: float = 0.0
    clip_level: float | None = None


def simulate_audio(duration_s: float, cfg: AudioFaultConfig = AudioFaultConfig(), seed: int = 13) -> dict[str,np.ndarray]:
    if duration_s<=0 or cfg.sample_rate_hz<=0 or cfg.channels<=0:raise ValueError('invalid audio duration/rate/channels')
    rng=np.random.default_rng(seed);n=int(np.floor(duration_s*cfg.sample_rate_hz));t=np.arange(n,dtype=np.float64)/cfg.sample_rate_hz
    base=0.03*np.sin(2*np.pi*cfg.tone_hz*t);x=np.repeat(base[:,None],cfg.channels,axis=1)+rng.normal(0,cfg.noise_std,(n,cfg.channels));valid=np.ones(n,bool)
    if cfg.dropout_start_s is not None:
        bad=(t>=cfg.dropout_start_s)&(t<cfg.dropout_start_s+cfg.dropout_duration_s);x[bad]=0;valid[bad]=False
    if cfg.clip_level is not None:x=np.clip(x,-abs(cfg.clip_level),abs(cfg.clip_level))
    return {'time_s':t.astype(np.float32),'samples':x.astype(np.float32),'valid':valid}
