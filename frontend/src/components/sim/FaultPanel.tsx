"use client";

import { useMemo, useState } from "react";
import { Zap } from "lucide-react";
import { useStore } from "@/lib/store";
import type { FaultType } from "@/lib/types";

const FAULTS: { value: FaultType; label: string }[] = [
  { value: "disable_device", label: "Disable Device" },
  { value: "disable_link", label: "Disable Link" },
  { value: "set_link_latency", label: "Set Link Latency" },
  { value: "remove_vlan", label: "Remove VLAN" },
  { value: "disable_bgp_peer", label: "Disable BGP Peer" },
];

export function FaultPanel() {
  const siteTopology = useStore((s) => s.siteTopology);
  const selectedSite = useStore((s) => s.selectedSite);
  const injectFault = useStore((s) => s.injectFault);
  const busy = useStore((s) => s.busy);

  const [type, setType] = useState<FaultType>("disable_device");
  const [fields, setFields] = useState<Record<string, string>>({});

  const devices = useMemo(() => siteTopology?.devices ?? [], [siteTopology]);
  const vlans = useMemo(() => siteTopology?.vlans ?? [], [siteTopology]);
  const inSite = !!siteTopology;

  const set = (k: string, v: string) => setFields((f) => ({ ...f, [k]: v }));

  async function submit() {
    let params: Record<string, unknown> = {};
    if (type === "disable_device") params = { device_id: fields.device_id };
    if (type === "disable_link") params = { source: fields.source, target: fields.target };
    if (type === "set_link_latency")
      params = { source: fields.source, target: fields.target, latency_ms: Number(fields.latency_ms || 0) };
    if (type === "remove_vlan")
      params = { vlan_id: Number(fields.vlan_id), site: selectedSite };
    if (type === "disable_bgp_peer")
      params = { device_id: fields.device_id, peer_ip: fields.peer_ip };
    const ok = await injectFault(type, params);
    if (ok) setFields({});
  }

  return (
    <div className="panel">
      <div className="panel-head justify-between">
        <span className="eyebrow">Fault Injection</span>
        {inSite && (
          <span className="chip">{selectedSite}</span>
        )}
      </div>
      <div className="space-y-2.5 p-3">
        <select
          className="field"
          value={type}
          onChange={(e) => {
            setType(e.target.value as FaultType);
            setFields({});
          }}
        >
          {FAULTS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>

        {!inSite && (type !== "disable_bgp_peer") && (
          <p className="rounded-lg border border-line bg-surface/60 px-2.5 py-2 text-[11px] text-faint">
            Open a site to pick devices, links, and VLANs — or use a quick scenario below.
          </p>
        )}

        {type === "disable_device" && (
          <DeviceSelect devices={devices} value={fields.device_id} onChange={(v) => set("device_id", v)} />
        )}

        {(type === "disable_link" || type === "set_link_latency") && (
          <div className="grid grid-cols-2 gap-2">
            <DeviceSelect devices={devices} value={fields.source} onChange={(v) => set("source", v)} placeholder="source" />
            <DeviceSelect devices={devices} value={fields.target} onChange={(v) => set("target", v)} placeholder="target" />
          </div>
        )}

        {type === "set_link_latency" && (
          <input
            className="field"
            type="number"
            placeholder="latency (ms) e.g. 500"
            value={fields.latency_ms ?? ""}
            onChange={(e) => set("latency_ms", e.target.value)}
          />
        )}

        {type === "remove_vlan" && (
          <select className="field" value={fields.vlan_id ?? ""} onChange={(e) => set("vlan_id", e.target.value)}>
            <option value="">Select VLAN…</option>
            {vlans.map((v) => (
              <option key={v.id} value={v.vlan_id}>
                {v.vlan_id} · {v.name}
              </option>
            ))}
          </select>
        )}

        {type === "disable_bgp_peer" && (
          <div className="grid grid-cols-1 gap-2">
            <DeviceSelect devices={devices} value={fields.device_id} onChange={(v) => set("device_id", v)} />
            <input className="field" placeholder="peer IP" value={fields.peer_ip ?? ""} onChange={(e) => set("peer_ip", e.target.value)} />
          </div>
        )}

        <button onClick={submit} disabled={busy} className="btn btn-danger w-full">
          <Zap className="h-3.5 w-3.5" /> Inject Fault
        </button>
      </div>
    </div>
  );
}

function DeviceSelect({
  devices,
  value,
  onChange,
  placeholder = "device",
}: {
  devices: { id: string; name: string }[];
  value?: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  if (devices.length === 0) {
    return (
      <input
        className="field"
        placeholder={`${placeholder} id`}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <select className="field" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}…</option>
      {devices.map((d) => (
        <option key={d.id} value={d.id}>{d.id}</option>
      ))}
    </select>
  );
}
