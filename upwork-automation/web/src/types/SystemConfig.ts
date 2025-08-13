export interface SystemConfig {
  daily_application_limit: number;
  min_hourly_rate: number;
  target_hourly_rate: number;
  min_client_rating: number;
  min_hire_rate: number;
  keywords_include: string[];
  keywords_exclude: string[];
  automation_enabled: boolean;
  notification_channels: string[];
}