// Type contracts mirrored from the Graphite FastAPI backend.

export type Health = "healthy" | "degraded" | "critical";
export type Status = "up" | "down" | "active" | "removed" | "degraded";
export type Severity = "critical" | "high" | "medium" | "low";

export interface SitePosition {
  x: number;
  y: number;
}

export interface GlobalSite {
  site: string;
  name: string;
  health: Health;
  device_count: number;
  devices_down: number;
  total_users: number;
  position: SitePosition;
}

export interface WanLink {
  source_site: string;
  target_site: string;
  source: string;
  target: string;
  link_id: string;
  latency_ms: number;
  bandwidth: string;
  status: Status;
}

export interface GlobalTopology {
  sites: GlobalSite[];
  wan_links: WanLink[];
}

export interface SiteDevice {
  id: string;
  name: string;
  device_type: string;
  status: Status;
}

export interface SiteLink {
  source: string;
  target: string;
  bandwidth: string;
  latency_ms: number;
  status: Status;
}

export interface SiteVlan {
  id: string;
  vlan_id: number;
  name: string;
  subnet: string;
  status: Status;
}

export interface SiteService {
  id: string;
  name: string;
  status: Status;
  criticality: Severity;
}

export interface SiteUserGroup {
  id: string;
  name: string;
  estimated_users: number;
}

export interface EndpointGroup {
  id: string;
  name: string;
  zone: string;
  vlan_id: number;
  estimated_users: number;
  device_breakdown: Record<string, number>;
  access_device: string | null;
}

export interface SiteTopology {
  site: string;
  site_name: string;
  devices: SiteDevice[];
  links: SiteLink[];
  vlans: SiteVlan[];
  services: SiteService[];
  user_groups: SiteUserGroup[];
  endpoint_groups?: EndpointGroup[];
}

export interface DeviceInfo {
  id: string;
  name: string;
  device_type: string;
  vendor: string;
  model: string;
  os: string;
  site: string;
  status: Status;
  management_ip: string;
  role: string;
}

export interface BlastRadiusResult {
  component_id: string;
  component_type: string;
  status: string;
  affected_devices: { id: string; name: string; impact: string }[];
  affected_services: { id: string; name: string; impact: string; reason?: string }[];
  affected_user_groups: {
    id: string;
    name: string;
    estimated_users: number;
    impact: string;
  }[];
  total_users_affected: number;
  severity: Severity;
  severity_factors: string[];
}

export interface MutationLogEntry {
  mutation_type?: string;
  type?: string;
  [key: string]: unknown;
}

// --- Agent streaming events -------------------------------------------------
export interface ThoughtEvent {
  type: "thought";
  content: string;
}
export interface ToolCallEvent {
  type: "tool_call";
  tool_name: string;
  parameters: Record<string, unknown>;
}
export interface ToolResultEvent {
  type: "tool_result";
  tool_name: string;
  result: Record<string, unknown>;
}
export interface FinalAnswerEvent {
  type: "final_answer";
  summary: string;
  root_cause: string;
  affected_components: {
    devices?: string[];
    services?: string[];
    users?: { count: number; groups: string[] };
  };
  severity: Severity;
  confidence: number;
  remediation: string[];
}
export interface ErrorEvent {
  type: "error";
  message: string;
}
export interface DoneEvent {
  type: "done";
}

export type AgentEvent =
  | ThoughtEvent
  | ToolCallEvent
  | ToolResultEvent
  | FinalAnswerEvent
  | ErrorEvent
  | DoneEvent;

// --- Fault injection --------------------------------------------------------
export type FaultType =
  | "disable_device"
  | "disable_link"
  | "remove_vlan"
  | "set_link_latency"
  | "disable_bgp_peer";

export interface MutateRequest {
  mutation_type: string;
  parameters: Record<string, unknown>;
}
