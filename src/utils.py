def format_time(ms: int) -> str:
    '''

    Converts milliseconds to a human-readable time format (HH:MM:SS)
    '''
    
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    # then compute remainder of hours and minutes

    hours_remaining = hours % 24
    minutes_remaining = minutes % 60

    return f'{days} days :{hours_remaining} hrs :{minutes_remaining} mins'



    