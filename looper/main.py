from nuclear.sublog import log, logerr

from looper.wire import wire_input_output


def main():
    with logerr():
        log.info('Starting looper...')
        wire_input_output()

    
if __name__ == '__main__':
    main()
