"use client";

import { useState, useEffect, useCallback } from "react";
import {
  NetworkLog,
  MonitorLog,
  RebootHistory,
  fetchNetworkLogs,
  fetchMonitorLogs,
  fetchRebootHistory,
} from "@/utils/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  RefreshCcw,
  Wifi,
  WifiOff,
  ThermometerIcon,
  RotateCw,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

const getMinuteKey = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");

  return `${year}-${month}-${day}-${hours}-${minutes}`;
};

const fillMissingMinutes = (
  logs: NetworkLog[],
  startDate: Date,
  endDate: Date
): NetworkLog[] => {
  const logsByMinute = new Map<string, NetworkLog>();

  logs.forEach((log) => {
    try {
      const date = new Date(log.timestamp);

      if (isNaN(date.getTime())) {
        console.warn("Invalid date found:", log.timestamp);
        return;
      }

      date.setSeconds(0, 0);
      const timeKey = getMinuteKey(date);

      if (
        !logsByMinute.has(timeKey) ||
        new Date(log.timestamp) > new Date(logsByMinute.get(timeKey)!.timestamp)
      ) {
        logsByMinute.set(timeKey, log);
      }
    } catch (error) {
      console.error("Error processing log entry:", error, log);
    }
  });

  const completeData: NetworkLog[] = [];

  const adjustedStart = new Date(startDate);
  adjustedStart.setSeconds(0, 0);

  const adjustedEnd = new Date(endDate);
  adjustedEnd.setSeconds(0, 0);

  let currentMinute = new Date(adjustedStart);

  while (currentMinute <= adjustedEnd) {
    const timeKey = getMinuteKey(currentMinute);

    const correctedMinute = new Date(currentMinute);
    correctedMinute.setHours(correctedMinute.getHours() + 1);
    const correctedTimeKey = getMinuteKey(correctedMinute);

    if (logsByMinute.has(correctedTimeKey)) {
      const matchedLog = logsByMinute.get(correctedTimeKey)!;
      const correctedLog = {
        ...matchedLog,
        original_timestamp: matchedLog.timestamp,
        timestamp: new Date(currentMinute).toISOString(),
      };

      completeData.push(
        correctedLog as NetworkLog & { original_timestamp?: string }
      );
    } else if (logsByMinute.has(timeKey)) {
      completeData.push(logsByMinute.get(timeKey)!);
    } else {
      completeData.push({
        id: -1,
        timestamp: new Date(currentMinute).toISOString(),
        connected: 0,
        wifi_signal_dBm: "0",
        ping_external_ms: "0",
        ping_router_ms: "0",
        temperature_C: "0",
        __placeholder: true,
      } as NetworkLog & { __placeholder: boolean });
    }

    currentMinute.setMinutes(currentMinute.getMinutes() + 1);
  }

  return completeData;
};

export default function NetworkPage() {
  const [networkLogs, setNetworkLogs] = useState<NetworkLog[]>([]);
  const [monitorLogs, setMonitorLogs] = useState<MonitorLog[]>([]);
  const [rebootHistory, setRebootHistory] = useState<RebootHistory[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "reboots">(
    "overview"
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [timeRange, setTimeRange] = useState<"24h" | "week">("24h");
  const { toast } = useToast();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Calculate the time range
      const now = new Date();
      let startDate: Date;
      let expectedMinutes: number;

      if (timeRange === "24h") {
        startDate = new Date(now);
        startDate.setHours(now.getHours() - 24);
        expectedMinutes = 24 * 60 + 1; // 1441 minutes (24 hours + 1 minute)
      } else {
        startDate = new Date(now);
        startDate.setDate(now.getDate() - 7);
        expectedMinutes = 7 * 24 * 60 + 1; // 10081 minutes (7 days + 1 minute)
      }


      const startDateISO = startDate.toISOString();
      const endDateISO = now.toISOString();


      // Always fetch reboot history (get more data to cover our full time range)
      const rebootResponse = await fetchRebootHistory(100, 1);

      // Filter to only include reboots within our time range
      const filteredReboots = rebootResponse.data.filter((reboot) => {
        const rebootDate = new Date(reboot.timestamp);
        return rebootDate >= startDate && rebootDate <= now;
      });

      setRebootHistory(filteredReboots);

      // Load data based on active tab
      if (activeTab === "overview") {
        // We'll collect all network logs here
        let allLogs: NetworkLog[] = [];
        let hasMorePages = true;
        let noDataCounter = 0;

        // IMPORTANT: Get the most recent data first (page 1)
        // This ensures we have the latest data even if we can't fetch everything
        const firstResponse = await fetchNetworkLogs(
          1000,
          startDateISO,
          endDateISO,
          1,
          true
        );

        // Sort this page by timestamp first to ensure correct order
        allLogs = [...firstResponse.data].sort(
          (a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );


        // Calculate total expected pages
        const totalPages = firstResponse.meta.pages;

        // We'll start fetching from page 2 since we already have page 1
        let currentPage = 2;

        // Now fetch additional pages if needed, but wait if we need them all
        while (hasMorePages && currentPage <= totalPages && noDataCounter < 3) {
          try {
            const networkResponse = await fetchNetworkLogs(
              1000,
              startDateISO,
              endDateISO,
              currentPage,
              true
            );

            // If this page has data, add it
            if (networkResponse.data.length > 0) {
              // Sort these logs by timestamp to ensure data integrity
              const sortedPageData = networkResponse.data.sort(
                (a, b) =>
                  new Date(a.timestamp).getTime() -
                  new Date(b.timestamp).getTime()
              );

              // Add to our collection
              allLogs = [...allLogs, ...sortedPageData];
              noDataCounter = 0; // Reset counter since we got data
            } else {
              // Page had no data, increment counter
              noDataCounter++;
            }

            // Move to next page
            currentPage++;

            // Safety check to prevent infinite loops
            if (currentPage > 20) break;
          } catch (error) {
            console.error(`Error fetching page ${currentPage}:`, error);
            noDataCounter++;
          }
        }

        // Use a Map to deduplicate logs by timestamp (in case we got duplicates from pagination)
        const uniqueLogsMap = new Map<string, NetworkLog>();

        // Add all logs to the map, keeping the latest version of duplicates
        allLogs.forEach((log) => {
          uniqueLogsMap.set(log.timestamp, log);
        });

        // Convert back to array and re-sort
        const uniqueLogs = Array.from(uniqueLogsMap.values());

        const sortedLogs = uniqueLogs.sort(
          (a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        // Create minute-by-minute data with filled gaps
        const filledData = fillMissingMinutes(sortedLogs, startDate, now);

        // Set the processed data
        setNetworkLogs(filledData);
      }
    } catch (error) {
      console.error("Failed to load data:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load network data.",
      });
    } finally {
      setLoading(false);
    }
  }, [activeTab, timeRange, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Calculate summary statistics
  const calculateStats = () => {
    if (!networkLogs.length) return null;

    const totalMinutes = networkLogs.length;

    // Count placeholders (server downtime)
    const placeholders = networkLogs.filter(
      (log) => (log as any).__placeholder
    ).length;

    // Count real logs (server uptime)
    const realLogs = totalMinutes - placeholders;

    // Count connected logs - only from real logs (network is considered up when connected=1)
    const connectedRealLogs = networkLogs.filter(
      (log) => !(log as any).__placeholder && Number(log.connected) === 1
    ).length;

    // Calculate network uptime as percentage of connected time among real logs
    // This properly excludes times when server was down (placeholders)
    const networkUptime =
      realLogs > 0 ? (connectedRealLogs / realLogs) * 100 : 0;

    // Calculate server uptime as percentage of real logs vs total minutes
    const serverUptime = (realLogs / totalMinutes) * 100;

    // Calculate average temperature (only from real logs)
    let avgTemp = 0;
    let tempReadings = 0;

    networkLogs.forEach((log) => {
      // Skip placeholders
      if (!(log as any).__placeholder) {
        avgTemp += parseFloat(log.temperature_C) || 0;
        tempReadings++;
      }
    });

    avgTemp = tempReadings > 0 ? avgTemp / tempReadings : 0;

    // Count disconnected logs (network is down but server is up)
    const disconnectedRealLogs = realLogs - connectedRealLogs;

    return {
      totalMinutes,
      realLogs,
      placeholders,
      connected: connectedRealLogs,
      disconnected: disconnectedRealLogs,
      networkUptime,
      serverUptime,
      avgTemp,
    };
  };

  const stats = calculateStats();

  // Group logs by hour for the timeline visualization
  const groupLogsByHour = () => {
    const groups: Record<
      string,
      {
        connected: number;
        disconnected: number;
        total: number;
        avgTemp: number;
        avgSignal: number;
        timestamp: number;
        hour: string;
      }
    > = {};

    networkLogs.forEach((log) => {
      const date = new Date(log.timestamp);
      const hourKey =
        timeRange === "24h"
          ? `${String(date.getHours()).padStart(2, "0")}:00`
          : `${String(date.getMonth() + 1).padStart(2, "0")}-${String(
              date.getDate()
            ).padStart(2, "0")}`;

      if (!groups[hourKey]) {
        groups[hourKey] = {
          connected: 0,
          disconnected: 0,
          total: 0,
          avgTemp: 0,
          avgSignal: 0,
          timestamp: date.getTime(),
          hour: hourKey,
        };
      }

      groups[hourKey].total += 1;
      if (Number(log.connected) === 1) {
        groups[hourKey].connected += 1;
      } else {
        groups[hourKey].disconnected += 1;
      }

      groups[hourKey].avgTemp += parseFloat(log.temperature_C) || 0;
      groups[hourKey].avgSignal += parseFloat(log.wifi_signal_dBm) || 0;
    });

    // Calculate averages
    Object.keys(groups).forEach((key) => {
      if (groups[key].total > 0) {
        groups[key].avgTemp = groups[key].avgTemp / groups[key].total;
        groups[key].avgSignal = groups[key].avgSignal / groups[key].total;
      }
    });

    return Object.values(groups).sort((a, b) => a.timestamp - b.timestamp);
  };

  const hourlyData = groupLogsByHour();

  // Prepare data for charts
  const prepareChartData = () => {
    if (networkLogs.length === 0) return [];

    // Group data into fewer points for cleaner charts
    const groupSize = Math.max(1, Math.floor(networkLogs.length / 30)); // Aim for ~30 data points
    const groupedData: any[] = [];

    // Data is already sorted by timestamp from our fillMissingMinutes function
    const sortedLogs = networkLogs;

    // Create a map of reboot timestamps for easy lookup
    const rebootTimestamps = new Map<string, RebootHistory>();
    rebootHistory.forEach((reboot) => {
      // Convert to a string key in the format YYYY-MM-DD-HH-MM
      const rebootDate = new Date(reboot.timestamp);
      const rebootKey = getMinuteKey(rebootDate);
      rebootTimestamps.set(rebootKey, reboot);
    });

    for (let i = 0; i < sortedLogs.length; i += groupSize) {
      const chunk = sortedLogs.slice(i, i + groupSize);
      if (chunk.length === 0) continue;

      const startTimestamp = new Date(chunk[0].timestamp);
      const endTimestamp = new Date(chunk[chunk.length - 1].timestamp);

      let connectedCount = 0;
      let realLogsCount = 0; // Count non-placeholder logs for accurate temperature
      let tempSum = 0;
      let hasReboot = false;
      let successfulReboot = false;

      // Check if any minute in this chunk contains a reboot
      for (let j = 0; j < chunk.length; j++) {
        const minuteDate = new Date(chunk[j].timestamp);
        const minuteKey = getMinuteKey(minuteDate);

        if (rebootTimestamps.has(minuteKey)) {
          hasReboot = true;
          successfulReboot = rebootTimestamps.get(minuteKey)!.success === 1;
          break;
        }
      }

      // Check if there are any reboots within this time chunk
      chunk.forEach((log) => {
        const isPlaceholder = (log as any).__placeholder;

        // Connected count (0 for placeholders)
        if (Number(log.connected) === 1) connectedCount++;

        // Only count real logs for temperature
        if (!isPlaceholder) {
          realLogsCount++;
          tempSum += parseFloat(log.temperature_C) || 0;
        }
      });

      // Format time based on selected range
      const formattedTime =
        timeRange === "24h"
          ? `${String(startTimestamp.getHours()).padStart(2, "0")}:${String(
              startTimestamp.getMinutes()
            ).padStart(2, "0")}`
          : `${String(startTimestamp.getMonth() + 1).padStart(2, "0")}/${String(
              startTimestamp.getDate()
            ).padStart(2, "0")}`;

      groupedData.push({
        time: formattedTime,
        timestamp: startTimestamp.getTime(),
        connectivity: (connectedCount / chunk.length) * 100,
        temperature: realLogsCount > 0 ? tempSum / realLogsCount : 0,
        // Flag to show if this chunk has any real logs (for styling)
        hasRealData: realLogsCount > 0,
        // Reboot markers
        hasReboot: hasReboot,
        rebootType: hasReboot
          ? successfulReboot
            ? "success"
            : "failure"
          : null,
      });
    }

    return groupedData;
  };

  const chartData = prepareChartData();

  // Helper for timestamp formatting that accounts for potential timezone mismatch
  const formatTimestamp = (timestamp: string) => {
    // Create a date from the timestamp
    const date = new Date(timestamp);

    // Use the display time property if available (for corrected logs)
    // This ensures the UI shows consistent timestamps aligned with local time
    return date.toLocaleString();
  };

  // Helper to determine signal strength rating
  const getSignalStrength = (dBm: number) => {
    if (dBm >= -50) return { text: "Excellent", bars: 4 };
    if (dBm >= -60) return { text: "Good", bars: 3 };
    if (dBm >= -70) return { text: "Fair", bars: 2 };
    return { text: "Poor", bars: 1 };
  };

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      // Check if this data point has real data or is a placeholder
      const dataPoint = payload[0]?.payload;
      const isPlaceholder = dataPoint && !(dataPoint.hasRealData ?? true);
      const hasReboot = dataPoint?.hasReboot;

      return (
        <div className="bg-background border p-2 rounded-md shadow-md text-xs">
          <p className="font-bold">{label}</p>

          {isPlaceholder ? (
            <p className="text-red-500">Server offline (no data)</p>
          ) : (
            <>
              {payload.map((entry: any, index: number) => (
                <p key={index} style={{ color: entry.color }}>
                  {entry.name}: {Number(entry.value).toFixed(1)}
                  {entry.name === "Connectivity"
                    ? "%"
                    : entry.name === "Temperature"
                    ? "°C"
                    : ""}
                </p>
              ))}

              {/* Show reboot info if applicable */}
              {hasReboot && (
                <p
                  className={
                    dataPoint.rebootType === "success"
                      ? "text-green-500"
                      : "text-red-500"
                  }
                >
                  {dataPoint.rebootType === "success"
                    ? "Successful Reboot"
                    : "Failed Reboot"}
                </p>
              )}
            </>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="container mx-auto p-4 max-w-md">
      <Toaster />
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Network Monitoring</h1>
        <Button
          onClick={loadData}
          variant="outline"
          size="icon"
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCcw className="h-4 w-4" />
          )}
        </Button>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as any)}
        className="mb-6"
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="overview" disabled={loading}>
            Overview
          </TabsTrigger>
          <TabsTrigger value="reboots" disabled={loading}>
            Reboots
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {activeTab === "overview" && (
        <>
          <Tabs
            defaultValue="24h"
            className="mb-6"
            onValueChange={(value) => setTimeRange(value as "24h" | "week")}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="24h" disabled={loading}>
                Last 24 Hours
              </TabsTrigger>
              <TabsTrigger value="week" disabled={loading}>
                Last Week
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {loading && networkLogs.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-40 gap-3">
              <Loader2 className="animate-spin h-8 w-8" />
              <p className="text-sm text-muted-foreground">
                {timeRange === "24h"
                  ? "Loading last 24 hours..."
                  : "Loading last week..."}
              </p>
            </div>
          ) : networkLogs.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-40 gap-3">
              <p className="text-sm text-muted-foreground">
                No data available for this time period
              </p>
              <Button onClick={loadData} variant="outline" size="sm">
                <RefreshCcw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </div>
          ) : (
            <>
              {stats && (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <Card>
                    <CardHeader className="pb-2 pt-4">
                      <CardTitle className="text-sm font-medium">
                        Network Uptime
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col items-center">
                        <span className="text-3xl font-bold">
                          {stats.networkUptime.toFixed(1)}%
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          {stats.connected}/{stats.totalMinutes} minutes
                          connected
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2 pt-4">
                      <CardTitle className="text-sm font-medium">
                        Server Uptime
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col items-center">
                        <span className="text-3xl font-bold">
                          {stats.serverUptime.toFixed(1)}%
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          {stats.realLogs} of {stats.totalMinutes} minutes
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {stats.placeholders} minutes missing
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2 pt-4">
                      <CardTitle className="text-sm font-medium flex items-center gap-1">
                        <ThermometerIcon className="h-3 w-3" /> Temperature
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col items-center">
                        <span className="text-2xl font-bold">
                          {stats.avgTemp.toFixed(1)}°C
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          {stats.avgTemp > 70
                            ? "Hot"
                            : stats.avgTemp > 60
                            ? "Warm"
                            : "Normal"}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2 pt-4">
                      <CardTitle className="text-sm font-medium flex items-center gap-1">
                        <RotateCw className="h-3 w-3" /> Recent Reboots
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col items-center">
                        <span className="text-2xl font-bold">
                          {rebootHistory.length}
                        </span>
                        <div className="text-xs text-muted-foreground mt-1">
                          Last:{" "}
                          {rebootHistory.length > 0
                            ? new Date(
                                rebootHistory[0].timestamp
                              ).toLocaleDateString()
                            : "None"}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Connectivity Chart */}
              {chartData.length > 0 && (
                <Card className="mb-6">
                  <CardHeader className="flex flex-row justify-between items-center pb-2">
                    <CardTitle className="text-base">
                      Connectivity Overview
                    </CardTitle>
                    {loading && (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="h-60 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={chartData}
                          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient
                              id="colorConnectivity"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="5%"
                                stopColor="#4ade80"
                                stopOpacity={0.8}
                              />
                              <stop
                                offset="95%"
                                stopColor="#4ade80"
                                stopOpacity={0.1}
                              />
                            </linearGradient>
                            <linearGradient
                              id="colorDowntime"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >
                              <stop
                                offset="5%"
                                stopColor="#f87171"
                                stopOpacity={0.5}
                              />
                              <stop
                                offset="95%"
                                stopColor="#f87171"
                                stopOpacity={0.1}
                              />
                            </linearGradient>
                          </defs>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#374151"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fontSize: 10 }}
                            interval={timeRange === "24h" ? 4 : 8}
                          />
                          <YAxis
                            domain={[0, 100]}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value) => `${value}%`}
                          />
                          <Tooltip
                            content={<CustomTooltip />}
                            formatter={(value, name) => {
                              if (name === "Connectivity") {
                                return [
                                  `${Number(value).toFixed(1)}%`,
                                  "Network Connected",
                                ];
                              }
                              return [value, name];
                            }}
                          />
                          <Area
                            type="monotone"
                            dataKey="connectivity"
                            name="Connectivity"
                            stroke="#4ade80"
                            fillOpacity={1}
                            fill="url(#colorConnectivity)"
                          />

                          {/* Reboot Markers */}
                          {chartData.map((entry, index) => {
                            if (entry.hasReboot) {
                              return (
                                <text
                                  key={`reboot-${index}`}
                                  x={`${
                                    index * (100 / chartData.length) +
                                    50 / chartData.length
                                  }%`}
                                  y={entry.rebootType === "success" ? 25 : 15}
                                  textAnchor="middle"
                                  fill={
                                    entry.rebootType === "success"
                                      ? "#22c55e"
                                      : "#ef4444"
                                  }
                                  fontSize={18}
                                >
                                  ↻
                                </text>
                              );
                            }
                            return null;
                          })}
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex justify-center gap-4 text-xs mt-2 flex-wrap">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 bg-green-500 opacity-80 rounded-full"></div>
                        <span>Connection Rate</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 bg-red-500 opacity-50 rounded-full"></div>
                        <span>Server Downtime</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-green-500 text-md">↻</span>
                        <span>Successful Reboot</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-red-500 text-md">↻</span>
                        <span>Failed Reboot</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Temperature Chart */}
              {chartData.length > 0 && (
                <Card className="mb-6">
                  <CardHeader className="flex flex-row justify-between items-center pb-2">
                    <CardTitle className="text-base">Temperature</CardTitle>
                    {loading && (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="h-60 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={chartData}
                          margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#374151"
                          />
                          <XAxis
                            dataKey="time"
                            tick={{ fontSize: 10 }}
                            interval={timeRange === "24h" ? 4 : 8}
                          />
                          <YAxis
                            domain={[30, 80]}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value) => `${value}°C`}
                          />
                          <Tooltip
                            content={<CustomTooltip />}
                            formatter={(value, name) => {
                              return [
                                `${Number(value).toFixed(1)}°C`,
                                "Temperature",
                              ];
                            }}
                          />
                          <Line
                            type="monotone"
                            dataKey="temperature"
                            name="Temperature"
                            stroke="#f87171"
                            strokeWidth={2}
                            dot={false}
                            // Only display temperature for points that have real data
                            // Skip rendering for placeholder data points
                            isAnimationActive={false}
                            connectNulls={true}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Status Change Events */}
              <Card>
                <CardHeader className="flex flex-row justify-between items-center pb-2">
                  <CardTitle className="text-base">
                    Connection Status Changes
                  </CardTitle>
                  {loading && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-60 overflow-y-auto">
                    {/* Filter to only show real logs (not placeholders) and only status changes */}
                    {(() => {
                      const realLogs = networkLogs.filter(
                        (log) => !(log as any).__placeholder
                      );
                      const statusChanges: any[] = [];

                      // Detect connection status changes
                      for (let i = 1; i < realLogs.length; i++) {
                        const prevStatus = Number(realLogs[i - 1].connected);
                        const currStatus = Number(realLogs[i].connected);

                        // If status changed, add this log to our list
                        if (prevStatus !== currStatus) {
                          statusChanges.push({
                            ...realLogs[i],
                            changeType:
                              currStatus === 1 ? "reconnected" : "disconnected",
                          });
                        }
                      }

                      // Return most recent changes first, limited to 10
                      return statusChanges.slice(0, 10).map((log) => (
                        <div
                          key={log.id}
                          className={`flex items-center gap-2 p-2 border rounded-md ${
                            log.changeType === "reconnected"
                              ? "border-green-800"
                              : "border-red-800"
                          }`}
                        >
                          {log.changeType === "reconnected" ? (
                            <Wifi className="h-4 w-4 text-green-500" />
                          ) : (
                            <WifiOff className="h-4 w-4 text-red-500" />
                          )}
                          <div className="grid gap-0.5">
                            <div className="text-sm font-medium">
                              {log.changeType === "reconnected"
                                ? "Network Reconnected"
                                : "Network Disconnected"}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {formatTimestamp(log.timestamp)}
                            </div>
                            <div className="text-xs">
                              <span>Temperature: {log.temperature_C}°C</span>
                            </div>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}

      {activeTab === "reboots" && (
        <>
          {loading ? (
            <div className="flex flex-col justify-center items-center h-40 gap-3">
              <Loader2 className="animate-spin h-8 w-8" />
              <p className="text-sm text-muted-foreground">
                Loading reboot history...
              </p>
            </div>
          ) : rebootHistory.length === 0 ? (
            <div className="flex flex-col justify-center items-center h-40 gap-3">
              <p className="text-sm text-muted-foreground">
                No reboot history available
              </p>
              <Button onClick={loadData} variant="outline" size="sm">
                <RefreshCcw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </div>
          ) : (
            <Card>
              <CardHeader className="flex flex-row justify-between items-center pb-2">
                <CardTitle className="text-base">Reboot History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[400px] overflow-y-auto">
                  {rebootHistory.map((reboot) => (
                    <div
                      key={reboot.id}
                      className="flex items-start gap-2 p-2 border rounded-md"
                    >
                      <div className="mt-1">
                        {reboot.success === 1 ? (
                          <RotateCw className="h-4 w-4 text-green-500" />
                        ) : (
                          <RotateCw className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <div className="grid gap-0.5 flex-1">
                        <div className="text-sm font-medium flex justify-between">
                          <span>
                            {reboot.success === 1
                              ? "Successful Reboot"
                              : "Failed Reboot"}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatTimestamp(reboot.timestamp)}
                          </span>
                        </div>
                        {reboot.notes && (
                          <div className="text-xs whitespace-pre-line">
                            {reboot.notes}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
