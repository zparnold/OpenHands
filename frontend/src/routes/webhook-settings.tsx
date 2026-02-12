import { WebhookManager } from "#/components/features/webhooks/webhook-manager";

function WebhookSettingsScreen() {
  return (
    <div className="flex flex-col grow overflow-auto">
      <WebhookManager />
    </div>
  );
}

export default WebhookSettingsScreen;
