"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import { Headphones, Mic, MicOff, Phone, PhoneCall, PhoneIncoming, PhoneOff, ShieldCheck, Volume2 } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

type PhoneState = "disconnected" | "connecting" | "registered" | "incoming" | "in_call" | "failed";

type PhoneConfig = {
  wsUrl: string;
  sipDomain: string;
  extension: string;
  password: string;
  displayName: string;
  target: string;
};

const initialConfig: PhoneConfig = {
  wsUrl: "ws://192.168.10.37:8088/ws",
  sipDomain: "192.168.10.37",
  extension: "1004",
  password: "",
  displayName: "Voxalia WebRTC Lab",
  target: "1002"
};

function timestamp() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function targetUri(target: string, domain: string) {
  const trimmed = target.trim();
  if (trimmed.startsWith("sip:")) return trimmed;
  return `sip:${trimmed}@${domain}`;
}

function connectionStatus(state: PhoneState) {
  if (state === "registered" || state === "incoming" || state === "in_call") {
    return { label: "Connected", light: "bg-green-500 shadow-[0_0_0_3px_rgba(34,197,94,0.18)]" };
  }

  if (state === "connecting") {
    return { label: "Connecting", light: "bg-amber-500 shadow-[0_0_0_3px_rgba(245,158,11,0.18)]" };
  }

  return { label: "Disconnected", light: "bg-red-500 shadow-[0_0_0_3px_rgba(239,68,68,0.18)]" };
}

export function WebRtcPhoneLab() {
  const [config, setConfig] = useState<PhoneConfig>(initialConfig);
  const [phoneState, setPhoneState] = useState<PhoneState>("disconnected");
  const [sessionLabel, setSessionLabel] = useState("No active call");
  const [incomingFrom, setIncomingFrom] = useState<string | null>(null);
  const [incomingCallVisible, setIncomingCallVisible] = useState(false);
  const [muted, setMuted] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [micIssue, setMicIssue] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const uaRef = useRef<any>(null);
  const sessionRef = useRef<any>(null);
  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);

  const canRegister = useMemo(
    () => Boolean(config.wsUrl.trim() && config.sipDomain.trim() && config.extension.trim() && config.password),
    [config]
  );
  const status = connectionStatus(phoneState);
  const hasSession = Boolean(sessionRef.current);

  const log = useCallback((message: string) => {
    setLogs((current) => [`${timestamp()} ${message}`, ...current].slice(0, 80));
  }, []);

  const updateConfig = (key: keyof PhoneConfig, value: string) => {
    setConfig((current) => ({ ...current, [key]: value }));
  };

  const clearSession = useCallback(
    (session: any | null, reason: string) => {
      if (session && sessionRef.current && sessionRef.current !== session) return;

      sessionRef.current = null;
      setIncomingFrom(null);
      setIncomingCallVisible(false);
      setMuted(false);
      setSessionLabel("No active call");
      if (remoteAudioRef.current) {
        remoteAudioRef.current.pause();
        remoteAudioRef.current.srcObject = null;
      }
      setPhoneState(uaRef.current?.isRegistered?.() ? "registered" : "disconnected");
      log(reason);
    },
    [log]
  );

  const monitorPeerConnection = useCallback(
    (session: any, connection: RTCPeerConnection | undefined | null) => {
      if (!connection || (connection as any).__voxaliaMonitored) return;
      (connection as any).__voxaliaMonitored = true;

      connection.addEventListener("connectionstatechange", () => {
        const state = connection.connectionState;
        log(`Peer connection state: ${state}`);
        if (state === "closed" || state === "failed" || state === "disconnected") {
          clearSession(session, `Call media connection ${state}`);
        }
      });

      connection.addEventListener("iceconnectionstatechange", () => {
        const state = connection.iceConnectionState;
        log(`ICE connection state: ${state}`);
        if (state === "closed" || state === "failed" || state === "disconnected") {
          clearSession(session, `Call ICE connection ${state}`);
        }
      });
    },
    [clearSession, log]
  );

  const attachRemoteAudio = useCallback(
    (session: any) => {
      const connection = session.connection;
      if (!connection || !remoteAudioRef.current) return;

      connection.addEventListener("track", (event: RTCTrackEvent) => {
        const [stream] = event.streams;
        if (!stream || !remoteAudioRef.current) return;
        remoteAudioRef.current.srcObject = stream;
        remoteAudioRef.current.play().catch((error) => log(`Remote audio play blocked: ${String(error)}`));
      });
    },
    [log]
  );

  const bindSession = useCallback(
    (session: any, direction: "incoming" | "outgoing") => {
      sessionRef.current = session;
      setPhoneState(direction === "incoming" ? "incoming" : "in_call");
      const remoteLabel =
        session.remote_identity?.display_name ||
        session.remote_identity?.uri?.user ||
        session.remote_identity?.uri?.toString?.() ||
        "Unknown caller";
      setIncomingFrom(direction === "incoming" ? String(remoteLabel) : null);
      setIncomingCallVisible(direction === "incoming");
      setSessionLabel(direction === "incoming" ? `Incoming call from ${remoteLabel}` : "Calling");
      log(direction === "incoming" ? "Incoming session created" : "Outgoing session created");
      attachRemoteAudio(session);
      monitorPeerConnection(session, session.connection);

      session.on("peerconnection", (event: any) => {
        log("Peer connection created");
        monitorPeerConnection(session, event?.peerconnection ?? session.connection);
      });

      session.on("progress", () => {
        setSessionLabel("Ringing");
        log("Call progress");
      });
      session.on("accepted", () => {
        setIncomingCallVisible(false);
        setPhoneState("in_call");
        setSessionLabel("In call");
        log("Call accepted");
      });
      session.on("confirmed", () => {
        setPhoneState("in_call");
        setSessionLabel("Media confirmed");
        log("Call confirmed");
      });
      session.on("ended", (event: any) => clearSession(session, `Call ended: ${event?.cause ?? "normal clearing"}`));
      session.on("failed", (event: any) => {
        clearSession(session, `Call failed: ${event?.cause ?? "unknown cause"}`);
      });
      session.on("bye", (event: any) => clearSession(session, `Remote BYE: ${event?.cause ?? "normal clearing"}`));
    },
    [attachRemoteAudio, clearSession, log, monitorPeerConnection]
  );

  const requestMicrophone = async () => {
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        const origin = window.location.origin;
        const message =
          `Microphone API unavailable from ${origin}. Open the lab from http://localhost:8320 on this machine, ` +
          "or serve Voxalia through HTTPS before using a LAN hostname/IP.";
        setMicIssue(message);
        setMicReady(false);
        setPhoneState("failed");
        log(message);
        return false;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      localStreamRef.current = stream;
      setMicReady(true);
      setMicIssue(null);
      log("Microphone permission granted");
      return true;
    } catch (error) {
      const message = `Microphone permission failed: ${String(error)}`;
      setMicReady(false);
      setPhoneState("failed");
      setMicIssue(message);
      log(message);
      return false;
    }
  };

  const register = async () => {
    if (!canRegister) {
      log("Missing WebSocket URL, SIP domain, extension or password");
      return;
    }

    if (!micReady) {
      const ready = await requestMicrophone();
      if (!ready) return;
    }

    try {
      setPhoneState("connecting");
      const JsSIPModule = await import("jssip");
      const JsSIP = ((JsSIPModule as any).default ?? JsSIPModule) as any;
      const socket = new JsSIP.WebSocketInterface(config.wsUrl.trim());
      const ua = new JsSIP.UA({
        sockets: [socket],
        uri: `sip:${config.extension.trim()}@${config.sipDomain.trim()}`,
        authorization_user: config.extension.trim(),
        password: config.password,
        display_name: config.displayName.trim() || config.extension.trim(),
        register: true,
        session_timers: false
      });

      ua.on("connected", () => log("WebSocket connected"));
      ua.on("disconnected", () => {
        setPhoneState("disconnected");
        log("WebSocket disconnected");
      });
      ua.on("registered", () => {
        setPhoneState("registered");
        log(`Registered extension ${config.extension}`);
      });
      ua.on("unregistered", () => {
        setPhoneState("disconnected");
        log("Unregistered");
      });
      ua.on("registrationFailed", (event: any) => {
        setPhoneState("failed");
        log(`Registration failed: ${event?.cause ?? "unknown cause"}`);
      });
      ua.on("newRTCSession", (event: any) => {
        const session = event.session;
        log(`RTC session originator: ${event.originator ?? "unknown"}`);
        if (sessionRef.current && sessionRef.current !== session) {
          session.terminate();
          log("Rejected extra session because one call is already active");
          return;
        }
        bindSession(session, event.originator === "remote" ? "incoming" : "outgoing");
      });

      ua.start();
      uaRef.current = ua;
      log("Starting SIP user agent");
    } catch (error) {
      setPhoneState("failed");
      log(`Registration setup failed: ${String(error)}`);
    }
  };

  const unregister = () => {
    sessionRef.current?.terminate?.();
    uaRef.current?.stop?.();
    uaRef.current = null;
    sessionRef.current = null;
    setIncomingFrom(null);
    setIncomingCallVisible(false);
    setPhoneState("disconnected");
    setSessionLabel("No active call");
    log("Stopped SIP user agent");
  };

  const call = () => {
    if (!uaRef.current?.isRegistered?.()) {
      log("Register before calling");
      return;
    }

    uaRef.current.call(targetUri(config.target, config.sipDomain), {
      mediaConstraints: { audio: true, video: false },
      rtcOfferConstraints: { offerToReceiveAudio: true, offerToReceiveVideo: false },
      pcConfig: { iceServers: [] }
    });
  };

  const answer = () => {
    if (!sessionRef.current) return;
    setIncomingCallVisible(false);
    sessionRef.current.answer({
      mediaConstraints: { audio: true, video: false },
      rtcOfferConstraints: { offerToReceiveAudio: true, offerToReceiveVideo: false },
      pcConfig: { iceServers: [] }
    });
    log("Answer requested");
  };

  const hangup = () => {
    const session = sessionRef.current;
    setIncomingCallVisible(false);
    session?.terminate?.();
    clearSession(session, "Hangup requested");
  };

  const toggleMute = () => {
    const nextMuted = !muted;
    if (nextMuted) {
      sessionRef.current?.mute?.({ audio: true });
    } else {
      sessionRef.current?.unmute?.({ audio: true });
    }
    setMuted(nextMuted);
    log(nextMuted ? "Muted local audio" : "Unmuted local audio");
  };

  useEffect(() => {
    return () => {
      uaRef.current?.stop?.();
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <div className="mb-2 flex flex-wrap gap-2">
            <div className="inline-flex h-7 items-center gap-2 rounded-md border bg-card px-2.5 text-label font-medium">
              <span className={`h-2.5 w-2.5 rounded-full ${status.light}`} aria-hidden="true" />
              <span>{status.label}</span>
            </div>
            <Badge>{phoneState}</Badge>
            <Badge>{micReady ? "microphone ready" : "microphone not checked"}</Badge>
            <Badge>Asterisk WebRTC lab</Badge>
          </div>
          <h1 className="text-page-title font-light">WebRTC Phone Lab</h1>
          <p className="mt-2 max-w-3xl text-page-subtitle text-muted-foreground">
            Browser softphone spike for validating the FreePBX-managed WebRTC extension against Asterisk without touching the working MicroSIP 1002 baseline.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={requestMicrophone}>
            <Mic className="h-4 w-4" />
            Check mic
          </Button>
          <Button type="button" onClick={register} disabled={!canRegister || phoneState === "registered" || phoneState === "in_call"}>
            <PhoneCall className="h-4 w-4" />
            Register
          </Button>
          <Button type="button" variant="outline" onClick={unregister} disabled={phoneState === "disconnected"}>
            <PhoneOff className="h-4 w-4" />
            Stop
          </Button>
        </div>
      </div>

      {micIssue ? (
        <Alert variant="warning" title="Microphone is not available">
          {micIssue}
        </Alert>
      ) : null}

      {incomingCallVisible ? (
        <div className="fixed right-4 top-4 z-50 w-[min(420px,calc(100vw-2rem))] rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-950 shadow-xl">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-500 text-white animate-pulse">
              <PhoneIncoming className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-card-title font-semibold">Incoming call</div>
              <div className="truncate text-body-sm">From {incomingFrom ?? "Unknown caller"}</div>
              <div className="mt-3 flex gap-2">
                <Button type="button" onClick={answer}>
                  <PhoneIncoming className="h-4 w-4" />
                  Answer
                </Button>
                <Button type="button" variant="outline" onClick={hangup}>
                  <PhoneOff className="h-4 w-4" />
                  Hang up
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {incomingCallVisible ? (
        <div className="flex flex-col gap-3 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-amber-950 shadow-[0_0_0_3px_rgba(245,158,11,0.14)] md:flex-row md:items-center md:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500 text-white animate-pulse">
              <PhoneIncoming className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="text-card-title font-semibold">Incoming call</div>
              <div className="truncate text-body-sm">From {incomingFrom ?? "Unknown caller"}</div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" onClick={answer}>
              <PhoneIncoming className="h-4 w-4" />
              Answer
            </Button>
            <Button type="button" variant="outline" onClick={hangup}>
              <PhoneOff className="h-4 w-4" />
              Hang up
            </Button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <div className="text-card-title font-medium">SIP configuration</div>
            <div className="mt-1 text-body-sm text-muted-foreground">Use the dedicated FreePBX WebRTC extension 1004. Do not reuse the working MicroSIP 1002 password here.</div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="WebSocket URL" value={config.wsUrl} onChange={(value) => updateConfig("wsUrl", value)} />
            <Field label="SIP domain" value={config.sipDomain} onChange={(value) => updateConfig("sipDomain", value)} />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Extension" value={config.extension} onChange={(value) => updateConfig("extension", value)} />
              <Field label="Target" value={config.target} onChange={(value) => updateConfig("target", value)} />
            </div>
            <Field label="Display name" value={config.displayName} onChange={(value) => updateConfig("displayName", value)} />
            <Field label="Password" value={config.password} onChange={(value) => updateConfig("password", value)} type="password" />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="text-card-title font-medium">Call controls</div>
              <div className="mt-1 text-body-sm text-muted-foreground">{sessionLabel}</div>
            </CardHeader>
            <CardContent>
              <audio ref={remoteAudioRef} autoPlay playsInline />
              <div className="grid gap-3 md:grid-cols-4">
                <Button type="button" onClick={call} disabled={phoneState !== "registered"}>
                  <Phone className="h-4 w-4" />
                  Call
                </Button>
                <Button type="button" variant="outline" onClick={answer} disabled={phoneState !== "incoming"}>
                  <PhoneIncoming className="h-4 w-4" />
                  Answer
                </Button>
                <Button type="button" variant="outline" onClick={toggleMute} disabled={!hasSession || phoneState === "incoming"}>
                  {muted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                  {muted ? "Unmute" : "Mute"}
                </Button>
                <Button type="button" variant="outline" onClick={hangup} disabled={!hasSession}>
                  <PhoneOff className="h-4 w-4" />
                  Hang up
                </Button>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <StatusCard icon={Headphones} label="Baseline" value="1002 MicroSIP stays intact" />
                <StatusCard icon={Volume2} label="Media" value="Browser audio via WebRTC" />
                <StatusCard icon={ShieldCheck} label="Recording" value="Expected Asterisk-side" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="text-card-title font-medium">Technical log</div>
              <div className="mt-1 text-body-sm text-muted-foreground">Use this output to tune Asterisk WSS/WebRTC, certificates, ICE and codecs.</div>
            </CardHeader>
            <CardContent>
              <div className="h-72 overflow-y-auto rounded-md border bg-background p-3 font-mono text-xs leading-5 text-ink-secondary">
                {logs.length ? logs.map((entry) => <div key={entry}>{entry}</div>) : <div>No events yet.</div>}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  type = "text",
  onChange
}: {
  label: string;
  value: string;
  type?: "text" | "password";
  onChange: (value: string) => void;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-body-sm font-medium">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-control w-full rounded-md border bg-background px-3 text-body-sm outline-none focus:ring-2 focus:ring-ring"
      />
    </label>
  );
}

function StatusCard({
  icon: Icon,
  label,
  value
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex min-h-20 items-center gap-3 rounded-md border bg-surface-2 p-3">
      <Icon className="h-4 w-4 text-semantic-blue" />
      <div>
        <div className="text-label text-muted-foreground">{label}</div>
        <div className="text-body-sm font-medium">{value}</div>
      </div>
    </div>
  );
}
