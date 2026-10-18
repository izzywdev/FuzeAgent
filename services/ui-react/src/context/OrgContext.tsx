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
  tier?: 'free' | 'pro' | 'enterprise' | string;
}

export interface OrgEventNotification {
  id: string;
  type: 'org:switched' | 'org:created' | 'org:deleted' | 'user:created' | 'user:deleted' | 'member:added' | 'member:removed';
  message: string;
  timestamp: number;
}

export interface OrgContextValue {
  activeOrg: Organization | null;
  isPersonal: boolean;
  user: OrgUser | null;
  organizations: Organization[];
  switchOrg: (orgId: string) => void;
  recentEvents: OrgEventNotification[];
  clearEvents: () => void;
  isPlatformMode: boolean;
  allowInAppOrgManagement: boolean; // Unleash kill-switch wrapped
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export const OrgProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [isPersonal, setIsPersonal] = useState<boolean>(true);
  const [user, setUser] = useState<OrgUser | null>(null);
  const [recentEvents, setRecentEvents] = useState<OrgEventNotification[]>([]);
  const [isPlatformMode, setIsPlatformMode] = useState<boolean>(false);
  
  // Unleash Feature Flag Kill-Switch: default OFF in platform mode so org management is delegated strictly to FuzeFront
  const [allowInAppOrgManagement, setAllowInAppOrgManagement] = useState<boolean>(false);

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

  // Sync state from snapshot/context
  const syncPlatformSnapshot = useCallback((snapshot: any) => {
    if (!snapshot) return;

    // Check Unleash kill-switch feature toggle
    const bridge = typeof window !== 'undefined' ? (window as any).__FUZEFRONT__ : null;
    const flagFromBridge = bridge?.features?.isEnabled?.('fuzeagent.in-app-org-management') ??
      bridge?.unleash?.isEnabled?.('fuzeagent.in-app-org-management') ?? false;
    setAllowInAppOrgManagement(Boolean(flagFromBridge));

    // Handle user identity
    if (snapshot.user) {
      setUser({
        id: snapshot.user.id || 'usr_current',
        email: snapshot.user.email || 'user@fuzefront.com',
        name: snapshot.user.name || snapshot.user.email?.split('@')[0] || 'User',
        roles: snapshot.user.roles || ['member'],
      });
    }

    // Handle Organization vs Personal Context
    // In FuzeFront: null activeOrganization means Personal account context
    if (snapshot.activeOrganization) {
      setActiveOrg({
        id: snapshot.activeOrganization.id,
        name: snapshot.activeOrganization.name || 'Organization',
        slug: snapshot.activeOrganization.slug || snapshot.activeOrganization.id,
        tier: snapshot.activeOrganization.tier || 'enterprise',
      });
      setIsPersonal(false);
    } else if (snapshot.activeOrganization === null || snapshot.activeOrganizationId === null || snapshot.isPersonal) {
      setActiveOrg(null);
      setIsPersonal(true);
    }
  }, []);

  // Initialize and subscribe to window.__FUZEFRONT__ host bridge
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const bridge = (window as any).__FUZEFRONT__;
    if (bridge) {
      setIsPlatformMode(true);

      // 1. Initial snapshot sync
      if (typeof bridge.getContext === 'function') {
        syncPlatformSnapshot(bridge.getContext());
      }

      // 2. Subscribe to general bridge updates
      const unsubBridge = bridge.subscribe?.((ctx: any) => {
        syncPlatformSnapshot(ctx);
        if (ctx.activeOrganization) {
          addEvent('org:switched', `Organization switched to ${ctx.activeOrganization.name}`);
        } else {
          addEvent('org:switched', `Switched to Personal Context`);
        }
      });

      // 3. onOrgSwitch listener
      const unsubOrg = bridge.onOrgSwitch?.((org: any) => {
        if (org) {
          setActiveOrg({
            id: org.id,
            name: org.name || 'Organization',
            slug: org.slug || org.id,
            tier: org.tier || 'pro',
          });
          setIsPersonal(false);
          addEvent('org:switched', `Organization switched to ${org.name}`);
        } else {
          setActiveOrg(null);
          setIsPersonal(true);
          addEvent('org:switched', `Switched to Personal Context`);
        }
      });

      // 4. onAccountSwitch listener
      const unsubAccount = bridge.onAccountSwitch?.((u: any) => {
        if (u) {
          setUser({
            id: u.id,
            email: u.email,
            name: u.name || u.email?.split('@')[0],
            roles: u.roles || [],
          });
          addEvent('user:created', `Account switched to ${u.email}`);
        }
      });

      // 5. Socket events for live tenant lifecycle
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
          if (activeOrg?.id === deletedId) {
            setActiveOrg(null);
            setIsPersonal(true);
          }
          addEvent('org:deleted', `Organization was deleted`);
        };

        const handleUserCreated = (payload: any) => {
          addEvent('user:created', `User registered: ${payload.email || payload.name}`);
        };

        const handleUserDeleted = (payload: any) => {
          addEvent('user:deleted', `User removed: ${payload.email || payload.id}`);
        };

        const handleMemberAdded = (payload: any) => {
          addEvent('member:added', `Member ${payload.email || payload.userId} added to organization`);
        };

        const handleMemberRemoved = (payload: any) => {
          addEvent('member:removed', `Member ${payload?.email || payload?.userId || ''} removed from organization`);
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
    } else {
      // Standalone dev mode: allow in-app switcher if running outside FuzeFront
      setIsPlatformMode(false);
      setAllowInAppOrgManagement(true);
      setUser({
        id: 'usr_dev',
        email: 'developer@local.test',
        name: 'Local Developer',
        roles: ['owner'],
      });
      setActiveOrg({
        id: 'org_dev_standalone',
        name: 'Local Dev Org',
        slug: 'dev-org',
        tier: 'enterprise',
      });
      setIsPersonal(false);
    }
  }, [syncPlatformSnapshot, addEvent, activeOrg?.id]);

  // Global DOM Event Listeners for FuzeFront portal shell broadcast events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleContextChange = (e: any) => {
      const detail = e.detail;
      if (detail) {
        syncPlatformSnapshot(detail);
      }
    };

    const handleOrgSwitch = (e: any) => {
      const detail = e.detail;
      if (detail?.organization) {
        setActiveOrg(detail.organization);
        setIsPersonal(false);
        addEvent('org:switched', `Switched organization: ${detail.organization.name}`);
      } else if (detail === null || detail?.organization === null || detail?.isPersonal) {
        setActiveOrg(null);
        setIsPersonal(true);
        addEvent('org:switched', `Switched to Personal Context`);
      }
    };

    const handleAccountSwitch = (e: any) => {
      const detail = e.detail;
      if (detail?.user) {
        setUser(detail.user);
        addEvent('user:created', `Account switched: ${detail.user.email}`);
      }
    };

    window.addEventListener('fuzefront:context:change', handleContextChange);
    window.addEventListener('fuzefront:organization:change', handleOrgSwitch);
    window.addEventListener('fuzefront:org-switched', handleOrgSwitch);
    window.addEventListener('fuzefront:organization-switched', handleOrgSwitch);
    window.addEventListener('fuzefront:account-switched', handleAccountSwitch);

    return () => {
      window.removeEventListener('fuzefront:context:change', handleContextChange);
      window.removeEventListener('fuzefront:organization:change', handleOrgSwitch);
      window.removeEventListener('fuzefront:org-switched', handleOrgSwitch);
      window.removeEventListener('fuzefront:organization-switched', handleOrgSwitch);
      window.removeEventListener('fuzefront:account-switched', handleAccountSwitch);
    };
  }, [syncPlatformSnapshot, addEvent]);

  const switchOrg = useCallback((orgId: string) => {
    if (!allowInAppOrgManagement) {
      console.warn('Organization switching is managed exclusively by the FuzeFront portal shell');
      return;
    }
    const target = organizations.find(o => o.id === orgId);
    if (target) {
      setActiveOrg(target);
      setIsPersonal(false);
      addEvent('org:switched', `Switched to ${target.name}`);
    }
  }, [allowInAppOrgManagement, organizations, addEvent]);

  return (
    <OrgContext.Provider
      value={{
        activeOrg,
        isPersonal,
        user,
        organizations,
        switchOrg,
        recentEvents,
        clearEvents,
        isPlatformMode,
        allowInAppOrgManagement,
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
