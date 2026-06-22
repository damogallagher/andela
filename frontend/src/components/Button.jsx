import styled from "styled-components";

import { theme } from "../styles.js";

export const PrimaryButton = styled.button`
  min-height: 40px;
  border: 1px solid ${theme.colors.teal};
  border-radius: 6px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  background: ${theme.colors.teal};
  font-weight: 800;
  text-decoration: none;
`;

export const SecondaryLink = styled.a`
  min-height: 40px;
  border: 1px solid ${theme.colors.teal};
  border-radius: 6px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0f3f3b;
  background: ${theme.colors.tealSoft};
  font-weight: 800;
  text-decoration: none;
`;

export const SubtleButton = styled.button`
  min-height: 34px;
  border: 1px solid ${theme.colors.borderStrong};
  border-radius: 6px;
  padding: 0 12px;
  color: #0f3f3b;
  background: #ffffff;
  font-weight: 800;
`;
