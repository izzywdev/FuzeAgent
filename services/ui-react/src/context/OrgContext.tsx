import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export interface OrgUser {
  id: string;
  email: string;
  name?: string;
  roles: string[];
}

export interface Organization {
  id: string;
  name: string;
  slug?: string;
  tier?: 'free' | 'pro' | 'enterprise';
}

export interface OrgEventNotification {
  id: string;
  type: 'org:switched' | 'org:created' | 'org:deleted' | 'user:created' | 'user:deleted' | 'member:added' | 'member:removed';
  message: string;
  timestamp: number;
}

export interface OrgContextValue {
  activeOrg: Organization | null;
  user: OrgUser | null;
  organizations: Organization[];
  switchOrg: (orgId: string) => void;
  recentEvents: OrgEventNotification[];
  clearEvents: () => void;
  isPlatformMode: boolean;
}

const DEFAULT_ORGS: Organization[] = [
  { id: '00000000-0000-0000-0000-000000000010', name: 'FuzeSuite Core Org', slug: 'fuzesuite', tier: 'enterprise' },
  { id: 'org_dev_team', name: 'Engineering & DevOps', slug: 'engineering', tier: 'pro' },
  { id: 'org_growth', name: 'Product & Growth', slug: 'growth', tier: 'pro' },
];

const DEFAULT_USER: OrgUser = {
  id: 'usr_izzy',
  email: 'izzy@fuzefront.com',
  name: 'Izzy W.',
  roles: ['admin', 'architect', 'owner'],
};

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export const OrgProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [organizations, setOrganizations] = useState<Organization[]>(DEFAULT_ORGS);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(DEFAULT_ORGS[0]);
  const [user, setUser] = useState<OrgUser | null>(DEFAULT_USER);
  const [recentEvents, setRecentEvents] = useState<OrgEventNotification[]>([]);
  const [isPlatformMode, setIsPlatformMode] = useState<boolean>(false);

  const addEvent = useCallback((type: OrgEventNotification['type'], message: string) => {
    const event: OrgEventNotification = {
      id: `evt_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      type,
      message,
      timestamp: Date.now(),
    };
    setRecentEvents(prev => [event, ...prev].slice(0, 20));
  }, []);

  const clearEvents = useCallback(() => {
    setRecentEvents([]);
  }, []);

  // Initialize from window.__FUZEFRONT__ bridge if loaded in portal shell
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const bridge = (window as any).__FUZEFRONT__;
    if (bridge) {
      setIsPlatformMode(true);
      const snapshot = bridge.getContext ? bridge.getContext() : null;
      if (snapshot) {
        if (snapshot.activeOrganization) {
          setActiveOrg(snapshot.activeOrganization);
        }
        if (snapshot.user) {
          setUser(snapshot.user);
        }
      }

      // Subscribe to bridge context updates
      const unsubBridge = bridge.subscribe?.((ctx: any) => {
        if (ctx.activeOrganization) {
          setActiveOrg(ctx.activeOrganization);
          addEvent('org:switched', `Organization switched to ${ctx.activeOrganization.name}`);
        }
        if (ctx.user) {
          setUser(ctx.user);
        }
      });

      // Subscribe to specific bridge hooks
      const unsubOrg = bridge.onOrgSwitch?.((org: any) => {
        if (org) {
          setActiveOrg(org);
          addEvent('org:switched', `Switched context to organization: ${org.name}`);
        }
      });

      const unsubAccount = bridge.onAccountSwitch?.((u: any) => {
        if (u) {
          setUser(u);
          addEvent('user:created', `Active account switched to ${u.email}`);
        }
      });

      // Socket event listeners on bridge.socket
      const socket = bridge.socket;
      if (socket && typeof socket.on === 'function') {
        const handleOrgCreated = (payload: any) => {
          const newOrg: Organization = {
            id: payload.id || `org_${Date.now()}`,
            name: payload.name || 'New Organization',
            slug: payload.slug,
          };
          setOrganizations(prev => [...prev.filter(o => o.id !== newOrg.id), newOrg]);
          addEvent('org:created', `New organization created: ${newOrg.name}`);
        };

        const handleOrgDeleted = (payload: any) => {
          const deletedId = payload.id || payload.organizationId;
          setOrganizations(prev => prev.filter(o => o.id !== deletedId));
          setActiveOrg(curr => (curr?.id === deletedId ? DEFAULT_ORGS[0] : curr));
          addEvent('org:deleted', `Organization ${payload.name || deletedId} was deleted`);
        };

        const handleUserCreated = (payload: any) => {
          addEvent('user:created', `New user registered: ${payload.email || payload.name}`);
        };

        const handleUserDeleted = (payload: any) => {
          addEvent('user:deleted', `User removed: ${payload.email || payload.id}`);
        };

        const handleMemberAdded = (payload: any) => {
          addEvent('member:added', `User ${payload.email || payload.userId} added to organization`);
        };

        const handleMemberRemoved = (payload: any) => {
          addEvent('member:removed', `User ${payload.email || payload.userId} removed from organization`);
        };

        socket.on('organization:created', handleOrgCreated);
        socket.on('organization:deleted', handleOrgDeleted);
        socket.on('user:created', handleUserCreated);
        socket.on('user:deleted', handleUserDeleted);
        socket.on('organization:member-added', handleMemberAdded);
        socket.on('organization:member-removed', handleMemberRemoved);
      }

      return () => {
        unsubBridge?.();
        unsubOrg?.();
        unsubAccount?.();
      };
    }
  }, [addEvent]);

  // Global DOM Event Listeners for FuzeFront shell events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOrgSwitch = (e: Event) => {
      const customEvent = e as CustomEvent;
      const detail = customEvent.detail;
      if (detail?.organization) {
        setActiveOrg(detail.organization);
        addEvent('org:switched', `Switched organization: ${detail.organization.name}`);
      } else if (detail?.organizationId) {
        const found = organizations.find(o => o.id === detail.organizationId);
        if (found) {
          setActiveOrg(found);
          addEvent('org:switched', `Switched organization: ${found.name}`);
        }
      }
    };

    const handleAccountSwitch = (e: Event) => {
      const customEvent = e as CustomEvent;
      const detail = customEvent.detail;
      if (detail?.user) {
        setUser(detail.user);
        addEvent('user:created', `Account switched: ${detail.user.email}`);
      }
    };

    window.addEventListener('fuzefront:org-switched', handleOrgSwitch);
    window.addEventListener('fuzefront:organization-switched', handleOrgSwitch);
    window.addEventListener('fuzefront:account-switched', handleAccountSwitch);

    return () => {
      window.removeEventListener('fuzefront:org-switched', handleOrgSwitch);
      window.removeEventListener('fuzefront:organization-switched', handleOrgSwitch);
      window.removeEventListener('fuzefront:account-switched', handleAccountSwitch);
    };
  }, [organizations, addEvent]);

  const switchOrg = useCallback((orgId: string) => {
    const target = organizations.find(o => o.id === orgId);
    if (target) {
      setActiveOrg(target);
      addEvent('org:switched', `Manually switched to ${target.name}`);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('fuzefront:org-switched', {
            detail: { organizationId: target.id, organization: target },
          })
        );
      }
    }
  }, [organizations, addEvent]);

  return (
    <OrgContext.Provider
      value={{
        activeOrg,
        user,
        organizations,
        switchOrg,
        recentEvents,
        clearEvents,
        isPlatformMode,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
};

export const useOrgContext = (): OrgContextValue => {
  const ctx = useContext(OrgContext);
  if (!ctx) {
    throw new Error('useOrgContext must be used within an OrgProvider');
  }
  return ctx;
};
