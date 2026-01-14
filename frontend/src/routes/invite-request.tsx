import React from "react";
import { useNavigate } from "react-router";
import { InviteService } from "#/api/invite-service/invite-service.api";
import OpenHandsLogoWhite from "#/assets/branding/openhands-logo-white.svg?react";
import { displaySuccessToast, displayErrorToast } from "#/utils/custom-toast-handlers";

export default function InviteRequestPage() {
  const navigate = useNavigate();
  const [email, setEmail] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isSubmitted, setIsSubmitted] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      displayErrorToast("Please enter your email address");
      return;
    }

    setIsSubmitting(true);
    try {
      await InviteService.createInviteRequest({ email, notes: notes || undefined });
      setIsSubmitted(true);
      displaySuccessToast("Your invite request has been submitted successfully!");
    } catch (error: any) {
      if (error.response?.status === 409) {
        displayErrorToast("An invite request with this email already exists");
      } else {
        displayErrorToast("Failed to submit invite request. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-base p-4">
        <div className="flex flex-col items-center w-full max-w-md gap-8">
          <OpenHandsLogoWhite width={106} height={72} />
          <div className="bg-neutral-900 p-8 rounded-lg shadow-lg w-full">
            <h1 className="text-2xl font-semibold text-white text-center mb-4">
              Request Submitted
            </h1>
            <p className="text-neutral-400 text-center mb-6">
              Thank you for your interest! Your invite request has been submitted
              and will be reviewed by our team. You will be notified via email when
              your request is approved.
            </p>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="w-full py-2 px-4 bg-neutral-700 hover:bg-neutral-600 text-white rounded transition-colors"
            >
              Return to Login
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main
      className="min-h-screen flex items-center justify-center bg-base p-4"
      data-testid="invite-request-page"
    >
      <div className="flex flex-col items-center w-full max-w-md gap-8">
        <OpenHandsLogoWhite width={106} height={72} />

        <div className="bg-neutral-900 p-8 rounded-lg shadow-lg w-full">
          <h1 className="text-2xl font-semibold text-white text-center mb-2">
            Request an Invite
          </h1>
          <p className="text-neutral-400 text-center mb-6">
            Enter your email address to request access to OpenHands
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-neutral-300 mb-2"
              >
                Email Address *
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                required
                className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div>
              <label
                htmlFor="notes"
                className="block text-sm font-medium text-neutral-300 mb-2"
              >
                Additional Information (Optional)
              </label>
              <textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Tell us about your interest in OpenHands..."
                rows={4}
                className="w-full px-4 py-2 bg-neutral-800 border border-neutral-700 rounded text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-neutral-700 disabled:cursor-not-allowed text-white rounded transition-colors font-medium"
            >
              {isSubmitting ? "Submitting..." : "Request Invite"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
            >
              Already have access? Sign in
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
