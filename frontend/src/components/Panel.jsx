import styled from "styled-components";

import { theme } from "../styles.js";

export const Panel = styled.section`
  border: 1px solid ${theme.colors.border};
  border-radius: 8px;
  background: ${theme.colors.panel};
  box-shadow: ${theme.shadow};
`;

export const SectionHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
`;

export const Eyebrow = styled.p`
  margin: 0 0 6px;
  color: ${theme.colors.muted};
  font-size: 0.77rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
`;

export const SectionTitle = styled.h2`
  margin: 0;
  color: ${theme.colors.text};
  font-size: 1.25rem;
  line-height: 1.2;
`;

export const EmptyText = styled.p`
  margin: 0;
  color: #607382;
`;
