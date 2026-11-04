import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ResearchOutlineEditor from '@/components/research/ResearchOutlineEditor'

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (value: string) => value }) }))

describe('research outline turn admission', () => {
  it('does not submit a new research request while the outline turn is streaming', () => {
    const confirm = vi.fn()
    const outline = [{ title: 'Original study methods', overview: 'Read primary evidence.' }]
    const view = render(<ResearchOutlineEditor outline={outline} topic="Synthetic fixture" onConfirm={confirm} disabled />)
    const start = screen.getByRole('button', { name: 'Start Research' })
    expect(start).toBeDisabled()
    fireEvent.click(start)
    expect(confirm).not.toHaveBeenCalled()
    view.rerender(<ResearchOutlineEditor outline={outline} topic="Synthetic fixture" onConfirm={confirm} disabled={false} />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Research' }))
    expect(confirm).toHaveBeenCalledExactlyOnceWith(outline)
  })
})
