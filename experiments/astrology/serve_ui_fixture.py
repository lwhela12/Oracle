"""Local-only UI verification server. Prose is labelled as a test fixture, never Gemini.

Run from the repository root with the isolated astrology Python environment.
The real calculation engine and offline city search remain active.
"""
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    os.environ['ORACLE_ASTROLOGY_ENABLED'] = '1'
    os.environ['ORACLE_ANALYTICS_ENABLED'] = '0'
    os.environ.pop('ORACLE_DATABASE_URL', None)
    from app import app
    import astrology.routes

    attempts = {}

    class FixtureOracle:
        def stream_chat(self, prompt):
            attempts[prompt] = attempts.get(prompt, 0) + 1
            parts = [
                '[[HEART]]\nThis is a **test interpretation**, created only to verify the interface. ',
                'Your calculated chart above is real; these words are a fixture.\n\n',
                '[[DEPTH]]\n### A moment of reflection\n\n',
                'This passage exercises the complete reading layout. It makes no personal prediction.\n\n',
                '### Room to explore\n\nSelect a planet to inspect its calculated placement and aspects. ',
                'Saving and reopening should preserve both the chart and this complete fixture text.\n\n',
                '[[QUOTE]]\nYour calculated chart above is real; these words are a fixture.',
            ]
            for index, part in enumerate(parts):
                time.sleep(0.25)
                if 'fixture:interrupt' in prompt and attempts[prompt] == 1 and index == 3:
                    raise RuntimeError('Intentional fixture interruption')
                yield part

    astrology.routes.GeminiOracle = FixtureOracle

    @app.after_request
    def label_fixture(response):
        response.headers['X-Oracle-Test-Fixture'] = '1'
        return response

    app.run(host='127.0.0.1', port=8885, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
