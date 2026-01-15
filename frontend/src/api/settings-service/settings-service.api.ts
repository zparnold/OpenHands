import { openHands } from "../open-hands-axios";
import { Settings } from "#/types/settings";

/**
 * Settings service for managing application settings
 */
class SettingsService {
  /**
   * Get the settings from the server or use the default settings if not found
   */
  static async getSettings(): Promise<Settings> {
    const { data } = await openHands.get<Settings>("/api/settings");
    return data;
  }

  /**
   * Save the settings to the server. Only valid settings are saved.
   * @param settings - the settings to save
   */
  static async saveSettings(settings: Partial<Settings>): Promise<boolean> {
    const data = await openHands.post("/api/settings", settings);
    return data.status === 200;
  }

  /**
   * Validate LLM configuration before saving
   * @param settings - the settings to validate
   * @returns Promise resolving to validation result with message
   */
  static async validateLlm(settings: Partial<Settings>): Promise<{ message: string; model: string }> {
    const { data } = await openHands.post<{ message: string; model: string }>(
      "/api/validate-llm",
      settings,
    );
    return data;
  }
}

export default SettingsService;
