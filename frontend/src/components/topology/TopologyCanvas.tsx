"use client";

import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  MarkerType,
  useReactFlow,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { useStore } from "@/lib/store";
import { layoutSiteDevices, scaleSitePosition } from "@/lib/topologyLayout";
import { SiteNode } from "./SiteNode";
import { DeviceNode } from "./DeviceNode";
import { CanvasOverlay } from "./CanvasOverlay";

const nodeTypes = { site: SiteNode, device: DeviceNode };

function edgeColor(status: string, latency?: number) {
  if (status === "down" || status === "removed") return "#F85149";
  if (status === "degraded") return "#F0883E";
  if (latency !== undefined && latency >= 200) return "#F0883E";
  return "#2C3D4D";
}

export function TopologyCanvas() {
  const view = useStore((s) => s.view);
  const global = useStore((s) => s.global);
  const siteTopology = useStore((s) => s.siteTopology);
  const blast = useStore((s) => s.blast);
  const showBlast = useStore((s) => s.showBlast);
  const selectedDevice = useStore((s) => s.selectedDevice);
  const openSite = useStore((s) => s.openSite);
  const selectDevice = useStore((s) => s.selectDevice);

  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const impactMap = useMemo(() => {
    const m = new Map<string, "down" | "isolated" | "degraded">();
    if (showBlast && blast) {
      for (const d of blast.affected_devices) {
        m.set(d.id, (d.impact as "down" | "isolated" | "degraded") ?? "down");
      }
    }
    return m;
  }, [blast, showBlast]);

  // Build nodes + edges whenever the underlying data or overlay changes.
  useEffect(() => {
    if (view === "global" && global) {
      const siteNodes: Node[] = global.sites.map((site) => ({
        id: `site-${site.site}`,
        type: "site",
        position: scaleSitePosition(site.position),
        data: { site },
        draggable: true,
      }));
      const wanEdges: Edge[] = global.wan_links.map((l) => ({
        id: `wan-${l.link_id}`,
        source: `site-${l.source_site}`,
        target: `site-${l.target_site}`,
        label: `${l.latency_ms}ms · ${l.bandwidth}`,
        animated: l.status === "up",
        style: {
          stroke: edgeColor(l.status, l.latency_ms),
          strokeWidth: 1.8,
          strokeDasharray: l.status === "down" ? "6 4" : undefined,
        },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 4,
      }));
      setNodes(siteNodes);
      setEdges(wanEdges);
    } else if (view === "site" && siteTopology) {
      // Build per-device endpoint group map for user badges.
      const epByDevice = new Map<string, { users: number; groups: typeof siteTopology.endpoint_groups }>();
      for (const eg of siteTopology.endpoint_groups ?? []) {
        if (!eg.access_device) continue;
        const prev = epByDevice.get(eg.access_device);
        epByDevice.set(eg.access_device, {
          users: (prev?.users ?? 0) + eg.estimated_users,
          groups: [...(prev?.groups ?? []), eg],
        });
      }

      const positioned = layoutSiteDevices(siteTopology.devices);
      const deviceNodes: Node[] = positioned.map((d) => ({
        id: d.id,
        type: "device",
        position: { x: d.x, y: d.y },
        selected: d.id === selectedDevice,
        data: {
          device: { id: d.id, name: d.name, device_type: d.device_type, status: d.status },
          impact: impactMap.get(d.id) ?? null,
          isSource: blast?.component_id === d.id,
          endpointInfo: epByDevice.get(d.id) ?? null,
        },
        draggable: true,
      }));
      const linkEdges: Edge[] = siteTopology.links.map((l, i) => ({
        id: `link-${l.source}-${l.target}-${i}`,
        source: l.source,
        target: l.target,
        type: "smoothstep",
        animated: l.status === "down",
        style: {
          stroke: edgeColor(l.status, l.latency_ms),
          strokeWidth: 1.6,
          strokeDasharray: l.status === "down" ? "6 4" : undefined,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor(l.status, l.latency_ms), width: 14, height: 14 },
      }));
      setNodes(deviceNodes);
      setEdges(linkEdges);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [view, global, siteTopology, impactMap, blast, selectedDevice, setNodes, setEdges]);

  // Fit the view when the graph identity changes (view / site switch).
  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 60);
    return () => clearTimeout(t);
  }, [view, siteTopology?.site, global?.sites.length, fitView]);

  return (
    <div className="absolute inset-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          if (node.type === "site") {
            const s = (node.data as { site: { site: string } }).site.site;
            void openSite(s);
          } else if (node.type === "device") {
            void selectDevice(node.id);
          }
        }}
        onPaneClick={() => selectDevice(null)}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
        fitView
        className="bg-transparent"
      >
        <Background variant={BackgroundVariant.Dots} gap={26} size={1} color="#1A2430" />
        <Controls showInteractive={false} position="bottom-right" />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(7,10,15,0.7)"
          nodeColor={(n) =>
            n.type === "site" ? "#33E6B0" : "#243140"
          }
          style={{ background: "#0C1118", border: "1px solid #1C2733", borderRadius: 10 }}
        />
      </ReactFlow>
      <CanvasOverlay />
    </div>
  );
}
