import { useQuery } from "@tanstack/react-query";
import { openHands } from "#/api/open-hands-axios";

interface CurrentUser {
  id: string | null;
  is_org_admin?: boolean;
}

export const useCurrentUser = () =>
  useQuery({
    queryKey: ["current-user"],
    queryFn: async (): Promise<CurrentUser> => {
      const { data } = await openHands.get<CurrentUser>("/api/v1/users/me");
      return data;
    },
    staleTime: 1000 * 60 * 10,
    gcTime: 1000 * 60 * 30,
    meta: {
      disableToast: true,
    },
  });
