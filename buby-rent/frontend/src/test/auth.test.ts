import { describe, expect, it } from "vitest";
import { decodeJwt, demoToken, getSession, isExpired, logout, setToken } from "@/lib/auth";

describe("JWT session", () => {
  it("decodes sub and ruolo from the token", () => {
    const p = decodeJwt(demoToken("operatore"));
    expect(p.ruolo).toBe("operatore");
    expect(p.sub).toBe("1");
  });
  it("treats an expired token as signed out", () => {
    expect(isExpired({ sub: "1", ruolo: "admin", exp: 1 })).toBe(true);
  });
  it("logout clears the session", () => {
    setToken(demoToken());
    expect(getSession()).not.toBeNull();
    logout();
    expect(getSession()).toBeNull();
  });
});
