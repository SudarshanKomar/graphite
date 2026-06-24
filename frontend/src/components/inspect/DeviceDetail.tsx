"use client";

import { Radar, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { deviceMeta } from "@/lib/deviceMeta";
import { StatusPill } from "@/components/ui/primitives";

export function DeviceDetail() {
  const info = useStore((s) => s.deviceInfo);
  const selectedDevice = useStore((s) => s.selectedDevice);
  const selectDevice = useStore((s) => s.selectDevice);
  const showBlastFor = useStore((s) => s.showBlastFor);

  if (!selectedDevice) return null;

  const meta = info ? deviceMeta(info.device_type) : null;
  const Icon = meta?.icon;

  return (
    <div className="panel border-signal/30">
      <div className="panel-head justify-between">
        <span className="flex items-center gap-1.5 eyebrow text-signal">
          {Icon && <Icon className="h-3.5 w-3.5" />} Device
        </span>
        <button onClick={() => selectDevice(null)} className="text-faint hover:text-ink" aria-label="Close">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="space-y-3 p-3">
        {!info ? (
          <div className="text-[11px] text-faint">Loading {selectedDevice}…</div>
        ) : (
          <>
            <div>
              <div className="font-mono text-[13px] font-medium text-ink">{info.id}</div>
              <div className="text-[11px] text-muted">{info.name}</div>
            </div>

            <div className="flex items-center justify-between">
              <span className="chip">{meta?.label ?? info.device_type}</span>
              <StatusPill status={info.status} />
            </div>

            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[11px]">
              <Row k="Vendor" v={info.vendor} />
              <Row k="Model" v={info.model} />
              <Row k="OS" v={info.os} />
              <Row k="Role" v={info.role} />
              <Row k="Mgmt IP" v={info.management_ip} mono />
              <Row k="Site" v={info.site} />
            </dl>

            <button
              onClick={() => showBlastFor(info.id, info.id)}
              className="btn w-full text-xs"
            >
              <Radar className="h-3.5 w-3.5" /> Compute blast radius
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <>
      <dt className="text-faint">{k}</dt>
      <dd className={`text-right text-ink ${mono ? "font-mono text-[10.5px]" : ""}`}>{v || "—"}</dd>
    </>
  );
}
