import React from 'react'
import { getBaseUrl } from './api.js'

// Given pieces_raw, generate elements to display images for each piece
export function SpacePieces({ space }) {
  const p = space.pieces_raw || []
  const elements = []

  const baseUrl = getBaseUrl()

  // Helper to add multiple copies of an image
  const addPiece = (count, imgName, title) => {
    for (let i = 0; i < count; i++) {
      elements.push(
        <img
          key={`${title}-${i}`}
          src={`${baseUrl}/assets/${imgName}`}
          alt={title}
          title={title}
          style={{ width: 20, height: 20, margin: 1 }}
        />
      )
    }
  }

  // 0: Govt Troops
  addPiece(p[0], 'Troops.png', 'GOVT Troops')
  // 1: Govt Police
  addPiece(p[1], 'Police.png', 'GOVT Police')
  // 2: M26 Underground
  addPiece(p[2], 'Guerrilla-26July.png', 'M26 Guerrilla (Underground)')
  // 3: M26 Active
  addPiece(p[3], 'Guerrilla-26July (Active).png', 'M26 Guerrilla (Active)')
  // 4: M26 Base
  addPiece(p[4], 'Base-26July.png', 'M26 Base')
  // 5: DR Underground
  addPiece(p[5], 'Guerrilla-Directorio.png', 'DR Guerrilla (Underground)')
  // 6: DR Active
  addPiece(p[6], 'Guerrilla-Directorio (Active).png', 'DR Guerrilla (Active)')
  // 7: DR Base
  addPiece(p[7], 'Base-Directorio.png', 'DR Base')
  // 8: Syndicate Underground
  addPiece(p[8], 'Guerrilla-Syndicate.png', 'Syndicate Guerrilla (Underground)')
  // 9: Syndicate Active
  addPiece(p[9], 'Guerrilla-Syndicate (Active).png', 'Syndicate Guerrilla (Active)')

  // Syndicate Casinos (Open/Closed logic)
  // Let's assume all C's are open initially, then we swap for closed based on closed_casinos
  const totalCasinos = p[10] || 0
  const closedCasinos = space.closed_casinos || 0
  const openCasinos = totalCasinos - closedCasinos

  addPiece(openCasinos, 'Base-Casino(Open).png', 'Syndicate Casino (Open)')
  addPiece(closedCasinos, 'Base-Casino.png', 'Syndicate Casino (Closed)')


  // Control Marker
  if (space.controlled_by === 1) addPiece(1, 'GOVT Control.png', 'GOVT Control')
  if (space.controlled_by === 2) addPiece(1, '26July Control.png', 'M26 Control')
  if (space.controlled_by === 3) addPiece(1, 'DR Control.png', 'DR Control')
  if (space.controlled_by === 4) addPiece(1, 'Syndicate Control.png', 'Syndicate Control')

  // Alignment
  if (space.alignment === 1) addPiece(1, 'Active Support.png', 'Active Support')
  if (space.alignment === 2) addPiece(1, 'Passive Support.png', 'Passive Support')
  if (space.alignment === 3) addPiece(1, 'Passive Opposition.png', 'Passive Opposition')
  if (space.alignment === 4) addPiece(1, 'Active Opposition.png', 'Active Opposition')

  // Markers
  if (space.terror > 0) {
    addPiece(space.terror, 'Terror.png', 'Terror')
  }
  if (space.sabotage) {
    addPiece(1, 'Sabotage.png', 'Sabotage')
  }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', pointerEvents: 'none' }}>
      {elements}
    </div>
  )
}
